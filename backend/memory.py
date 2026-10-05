"""Saved chat history for logged-in shoppers (the chat_messages table).

Each assistant row stores its reply text in `content` and the structured reply
(type, product cards, search matches, options, price, stock) as JSON in
`products_json`. Older rows stored a plain list of product dicts there; those are
read back as product recommendations.
"""

import json

from db import get_db
from models import ChatHistoryItem, ChatResponse, HistoryMessage, PastChatMessage
from tools import card_from_db

MODEL_HISTORY_LIMIT = 10  # messages sent to the model as conversation context (kept short to save tokens)
PAGE_HISTORY_LIMIT = 100  # messages shown in the chat panel


def save_exchange(user_id: int, user_message: str, reply: ChatResponse) -> None:
    payload = reply.model_dump(exclude={"reply"}, mode="json")
    with get_db() as conn:
        conn.execute(
            "INSERT INTO chat_messages (user_id, role, content, products_json) VALUES (?, 'user', ?, NULL)",
            (user_id, user_message),
        )
        conn.execute(
            "INSERT INTO chat_messages (user_id, role, content, products_json) VALUES (?, 'assistant', ?, ?)",
            (user_id, reply.reply, json.dumps(payload)),
        )


def clear_history(user_id: int) -> int:
    with get_db() as conn:
        return conn.execute("DELETE FROM chat_messages WHERE user_id = ?", (user_id,)).rowcount


def _parse_reply(content: str, raw: str | None) -> ChatResponse | None:
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if isinstance(data, list):
        # Legacy rows: a list of product dicts. Rebuild cards from the database.
        cards = [c for p in data if isinstance(p, dict) and (c := card_from_db(str(p.get("product_id", ""))))]
        return ChatResponse(type="product_recommendation" if cards else "text", reply=content, products=cards)
    if isinstance(data, dict):
        try:
            return ChatResponse(reply=content, **data)
        except ValueError:
            return None
    return None


def _rows(user_id: int, limit: int):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, role, content, products_json, created_at FROM chat_messages "
            "WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return list(reversed(rows))


def load_history(user_id: int, limit: int = PAGE_HISTORY_LIMIT) -> list[HistoryMessage]:
    return [
        HistoryMessage(
            id=r["id"],
            role=r["role"],
            content=r["content"],
            created_at=r["created_at"],
            reply=_parse_reply(r["content"], r["products_json"]) if r["role"] == "assistant" else None,
        )
        for r in _rows(user_id, limit)
        if r["role"] in ("user", "assistant")
    ]


def _products_shown(reply: ChatResponse | None) -> list[str]:
    if reply is None:
        return []
    items = [(p.name, p.id) for p in reply.products] + [(m.name, m.id) for m in reply.matches]
    if reply.price:
        items.append((reply.price.name, reply.price.id))
    if reply.stock:
        items.append((reply.stock.name, reply.stock.id))
    return [f"{name} ({pid})" for name, pid in items]


def model_history(user_id: int) -> list[ChatHistoryItem]:
    """Recent messages for the model, with the products each reply showed so "that one" makes sense."""
    items = []
    for m in load_history(user_id, MODEL_HISTORY_LIMIT):
        content = m.content
        shown = _products_shown(m.reply)
        if shown:
            more = f", +{len(shown) - 5} more" if len(shown) > 5 else ""
            content += f"\n[Products shown: {', '.join(shown[:5])}{more}]"
        items.append(ChatHistoryItem(role=m.role, content=content[:1500]))
    return items


def search_past_chats(user_id: int, query: str = "", limit: int = 8) -> list[PastChatMessage]:
    """Older saved messages (newest first), optionally only those mentioning `query`."""
    limit = max(1, min(limit, 20))
    sql = "SELECT role, content, products_json, created_at FROM chat_messages WHERE user_id = ?"
    args: list = [user_id]
    if query.strip():
        sql += " AND (content LIKE ? OR products_json LIKE ?)"
        args += [f"%{query.strip()}%"] * 2
    sql += " ORDER BY id DESC LIMIT ?"
    args.append(limit)
    with get_db() as conn:
        rows = conn.execute(sql, args).fetchall()
    return [
        PastChatMessage(
            role=r["role"],
            content=r["content"][:600],
            created_at=r["created_at"],
            products_shown=_products_shown(_parse_reply(r["content"], r["products_json"]))[:10],
        )
        for r in rows
        if r["role"] in ("user", "assistant")
    ]
