"""Reset a user's password (stores a new PBKDF2 hash, never the plain text).

Run from the backend/ folder:
    python -m set_password <email>
You'll be prompted for the new password; it isn't echoed or saved anywhere.
"""

import getpass
import sys

from auth import hash_password
from db import get_db


def set_password(email: str, password: str) -> bool:
    with get_db() as conn:
        cur = conn.execute(
            "UPDATE users SET password_hash = ? WHERE email = ?",
            (hash_password(password), email.strip().lower()),
        )
        # Log out any existing sessions for this account.
        conn.execute(
            "DELETE FROM sessions WHERE user_id = (SELECT id FROM users WHERE email = ?)",
            (email.strip().lower(),),
        )
    return cur.rowcount == 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python -m set_password <email>")
    new_password = getpass.getpass("New password: ")
    if new_password != getpass.getpass("Confirm password: "):
        sys.exit("Passwords do not match.")
    if set_password(sys.argv[1], new_password):
        print("Password updated.")
    else:
        sys.exit("No user with that email.")
