"""Campus Customs API.

Run from the backend/ folder (with the HW 4 .venv activated):
    uvicorn main:app --reload --port 8000
"""

import asyncio
import json
import logging
import sqlite3
from pathlib import Path

from fastapi import Cookie, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic_ai.exceptions import AgentRunError, ModelAPIError, UsageLimitExceeded

from agent import AgentConfigError, AgentGaveUp, run_agent
from auth import init_auth_tables, router as auth_router, user_from_session
from db import DATA_DIR, get_db
from memory import clear_history, load_history, model_history, save_exchange
from models import (
    AgentReply,
    ChatDeps,
    ChatHistoryResponse,
    ChatRequest,
    ChatResponse,
    ClarifyingQuestionReply,
    PriceReply,
    ProductRecommendationReply,
    ProductSearchReply,
    StockReply,
)

log = logging.getLogger("campus_customs.api")

SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL"]

app = FastAPI(title="Campus Customs API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Product photos live in data/products; catalogue.image_file_path is relative to data/.
app.mount("/images", StaticFiles(directory=DATA_DIR / "products"), name="images")

init_auth_tables()
app.include_router(auth_router)


def product_from_row(row: sqlite3.Row) -> dict:
    product = dict(row)
    product["colors"] = json.loads(product["colors"])
    product["search_tags"] = json.loads(product["search_tags"])
    product["image_url"] = "/images/" + Path(product["image_file_path"]).name
    return product


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/products")
def list_products():
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT c.*, COALESCE(SUM(i.quantity), 0) AS total_stock
            FROM catalogue c
            LEFT JOIN inventory i ON i.product_id = c.product_id
            GROUP BY c.product_id
            ORDER BY c.name
            """
        ).fetchall()
    return [product_from_row(r) for r in rows]


@app.get("/api/products/{product_id}")
def get_product(product_id: str):
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM catalogue WHERE product_id = ?", (product_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Product not found")
        inventory = conn.execute(
            "SELECT size, quantity FROM inventory WHERE product_id = ?", (product_id,)
        ).fetchall()

    product = product_from_row(row)
    sizes = sorted(
        (dict(r) for r in inventory),
        key=lambda s: SIZE_ORDER.index(s["size"]) if s["size"] in SIZE_ORDER else len(SIZE_ORDER),
    )
    product["inventory"] = sizes
    product["total_stock"] = sum(s["quantity"] for s in sizes)
    return product


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    if request.url.path == "/api/chat":
        return JSONResponse(
            status_code=422,
            content={"detail": 'Please send a JSON body like {"message": "your question"} (1-2000 characters).'},
        )
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


def to_chat_response(reply: AgentReply) -> ChatResponse:
    # PriceReply and StockReply are TextReply subtypes, so check them first.
    if isinstance(reply, PriceReply):
        return ChatResponse(type=reply.type, reply=reply.message, price=reply.price_info)
    if isinstance(reply, StockReply):
        return ChatResponse(type=reply.type, reply=reply.message, stock=reply.stock_info)
    if isinstance(reply, ProductSearchReply):
        return ChatResponse(
            type=reply.type,
            reply=reply.message,
            search_label=reply.label,
            matches=reply.matches,
            total_matches=reply.total_matches,
        )
    if isinstance(reply, ProductRecommendationReply):
        return ChatResponse(type=reply.type, reply=reply.message, products=reply.products)
    if isinstance(reply, ClarifyingQuestionReply):
        return ChatResponse(type=reply.type, reply=reply.question, options=reply.options)
    return ChatResponse(type=reply.type, reply=reply.message)


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, cc_session: str | None = Cookie(default=None)):
    message = req.message.strip()
    if not message:
        raise HTTPException(422, "Message can't be empty.")

    # Logged-in shoppers: history comes from the database and the exchange is saved.
    # Guests: the browser sends the current conversation and nothing is saved.
    user = user_from_session(cc_session)
    history = model_history(user["id"]) if user else req.history
    deps = ChatDeps(user=user, page=req.page)

    try:
        reply = await run_agent(message, history, deps)
    except AgentGaveUp as gave_up:
        # Safety rule: after 3 failed attempts the agent stops and a person reviews the request.
        response = ChatResponse(
            type="text",
            reply=(
                "Sorry, I couldn't sort that out after a few tries, so I've passed it to the Campus Customs "
                f"team to look at (reference {gave_up.report_id}). Is there anything else I can help you find?"
            ),
        )
        if user:
            save_exchange(user["id"], message, response)
        return response
    except AgentConfigError:
        log.exception("Agent is not configured")
        raise HTTPException(503, "The shopping assistant isn't configured right now. Please try again later.")
    except asyncio.TimeoutError:
        raise HTTPException(504, "The shopping assistant took too long to respond. Please try again.")
    except UsageLimitExceeded:
        log.exception("Agent hit its request limit")
        raise HTTPException(502, "The shopping assistant couldn't finish that request. Try asking a bit more simply.")
    except (ModelAPIError, AgentRunError):
        log.exception("Agent run failed")
        raise HTTPException(502, "The shopping assistant is having trouble right now. Please try again in a moment.")
    except Exception:
        log.exception("Unexpected error in /api/chat")
        raise HTTPException(500, "Something went wrong on our end. Please try again.")

    response = to_chat_response(reply)
    if user:
        save_exchange(user["id"], message, response)
    return response


def _require_user(cc_session: str | None) -> dict:
    user = user_from_session(cc_session)
    if user is None:
        raise HTTPException(401, "Log in to see your saved chat history.")
    return user


@app.get("/api/chat/history", response_model=ChatHistoryResponse)
def chat_history(cc_session: str | None = Cookie(default=None)):
    user = _require_user(cc_session)
    return ChatHistoryResponse(messages=load_history(user["id"]))


@app.delete("/api/chat/history")
def delete_chat_history(cc_session: str | None = Cookie(default=None)):
    user = _require_user(cc_session)
    return {"deleted": clear_history(user["id"])}
