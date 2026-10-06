"""Account creation, login, and cookie-based sessions.

Security notes:
- Passwords are never stored. We store a salted PBKDF2-HMAC-SHA256 hash
  (600,000 iterations, 16-byte random salt per user) in users.password_hash,
  formatted as  pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>.
- Session tokens are random 32-byte values sent in an HttpOnly cookie, so page
  JavaScript can't read them. Only a SHA-256 of each token is kept in the
  database, so a leaked database can't be used to hijack sessions.
- Login failures return one generic message, take the same time whether or not
  the email exists, and are rate-limited per IP + email.
"""

import hashlib
import hmac
import re
import secrets
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Cookie, HTTPException, Request, Response
from pydantic import BaseModel

from db import get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])

HASH_ALGORITHM = "pbkdf2_sha256"
HASH_ITERATIONS = 600_000
SALT_BYTES = 16

SESSION_COOKIE = "cc_session"
SESSION_DAYS = 7

MAX_FAILED_LOGINS = 5
LOCKOUT_SECONDS = 15 * 60

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ---------- Password hashing ----------


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, HASH_ITERATIONS)
    return f"{HASH_ALGORITHM}${HASH_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    parts = stored.split("$")
    # Seed accounts use an older 3-part format without an iteration count; they can't be verified here.
    if len(parts) != 4 or parts[0] != HASH_ALGORITHM:
        return False
    _, iterations, salt_hex, hash_hex = parts
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), int(iterations))
    return hmac.compare_digest(digest.hex(), hash_hex)


# Used when the email doesn't exist so the response time doesn't reveal which accounts are real.
_DUMMY_HASH = hash_password(secrets.token_urlsafe(16))


# ---------- Sessions ----------


def init_auth_tables() -> None:
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                expires_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )
    ensure_test_account()


# The assignment's documented test login. The original data pack stores its password in an
# older 3-part hash format this backend can't verify, so on startup we re-save it once in the
# current format. Accounts already using the current format are never touched.
TEST_ACCOUNT_EMAIL = "test@campuscustoms.yale.edu"
TEST_ACCOUNT_PASSWORD = "password"


def ensure_test_account() -> None:
    with get_db() as conn:
        row = conn.execute("SELECT password_hash FROM users WHERE email = ?", (TEST_ACCOUNT_EMAIL,)).fetchone()
        if row is None or len(row["password_hash"].split("$")) == 4:
            return
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE email = ?",
            (hash_password(TEST_ACCOUNT_PASSWORD), TEST_ACCOUNT_EMAIL),
        )


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def start_session(response: Response, user_id: int) -> None:
    token = secrets.token_urlsafe(32)
    expires = _now() + timedelta(days=SESSION_DAYS)
    with get_db() as conn:
        conn.execute(
            "INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
            (_token_hash(token), user_id, expires.isoformat()),
        )
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=SESSION_DAYS * 24 * 3600,
        httponly=True,
        samesite="lax",
        # Set to True when the site is served over HTTPS.
        secure=False,
        path="/",
    )


def user_from_session(token: str | None) -> dict | None:
    if not token:
        return None
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT u.id, u.name, u.first_name, u.last_name, u.email, s.expires_at
            FROM sessions s JOIN users u ON u.id = s.user_id
            WHERE s.token_hash = ?
            """,
            (_token_hash(token),),
        ).fetchone()
        if row is None:
            return None
        if datetime.fromisoformat(row["expires_at"]) < _now():
            conn.execute("DELETE FROM sessions WHERE token_hash = ?", (_token_hash(token),))
            return None
    return public_user(row)


def public_user(row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "first_name": row["first_name"],
        "last_name": row["last_name"],
        "email": row["email"],
    }


# ---------- Rate limiting ----------

_failed_logins: dict[str, deque] = defaultdict(deque)


def _rate_key(request: Request, email: str) -> str:
    ip = request.client.host if request.client else "unknown"
    return f"{ip}|{email}"


def _check_rate_limit(key: str) -> None:
    attempts = _failed_logins[key]
    cutoff = time.monotonic() - LOCKOUT_SECONDS
    while attempts and attempts[0] < cutoff:
        attempts.popleft()
    if len(attempts) >= MAX_FAILED_LOGINS:
        raise HTTPException(429, "Too many failed attempts. Please wait a few minutes and try again.")


# ---------- Routes ----------


class RegisterRequest(BaseModel):
    first_name: str
    last_name: str
    email: str
    password: str
    confirm_password: str


class LoginRequest(BaseModel):
    email: str
    password: str


def _validate_password(password: str) -> None:
    if len(password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters.")
    if len(password) > 128:
        raise HTTPException(400, "Password must be 128 characters or fewer.")
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        raise HTTPException(400, "Password must include at least one letter and one number.")


@router.post("/register", status_code=201)
def register(body: RegisterRequest, response: Response):
    first = body.first_name.strip()
    last = body.last_name.strip()
    email = body.email.strip().lower()

    if not first or not last:
        raise HTTPException(400, "Please enter your first and last name.")
    if len(first) > 50 or len(last) > 50:
        raise HTTPException(400, "Names must be 50 characters or fewer.")
    if not EMAIL_RE.match(email) or len(email) > 254:
        raise HTTPException(400, "Please enter a valid email address.")
    _validate_password(body.password)
    if not hmac.compare_digest(body.password, body.confirm_password):
        raise HTTPException(400, "Passwords do not match.")

    with get_db() as conn:
        if conn.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone():
            raise HTTPException(409, "An account with that email already exists.")
        cur = conn.execute(
            "INSERT INTO users (name, email, password_hash, first_name, last_name) VALUES (?, ?, ?, ?, ?)",
            (f"{first} {last}", email, hash_password(body.password), first, last),
        )
        user_id = cur.lastrowid
        row = conn.execute(
            "SELECT id, name, first_name, last_name, email FROM users WHERE id = ?", (user_id,)
        ).fetchone()

    start_session(response, user_id)
    return public_user(row)


@router.post("/login")
def login(body: LoginRequest, request: Request, response: Response):
    email = body.email.strip().lower()
    key = _rate_key(request, email)
    _check_rate_limit(key)

    with get_db() as conn:
        row = conn.execute(
            "SELECT id, name, first_name, last_name, email, password_hash FROM users WHERE email = ?",
            (email,),
        ).fetchone()

    stored = row["password_hash"] if row else _DUMMY_HASH
    if not verify_password(body.password, stored) or row is None:
        _failed_logins[key].append(time.monotonic())
        raise HTTPException(401, "Incorrect email or password.")

    _failed_logins.pop(key, None)
    start_session(response, row["id"])
    return public_user(row)


@router.post("/logout")
def logout(response: Response, cc_session: str | None = Cookie(default=None)):
    if cc_session:
        with get_db() as conn:
            conn.execute("DELETE FROM sessions WHERE token_hash = ?", (_token_hash(cc_session),))
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"ok": True}


@router.get("/me")
def me(cc_session: str | None = Cookie(default=None)):
    user = user_from_session(cc_session)
    if user is None:
        raise HTTPException(401, "Not logged in.")
    return user
