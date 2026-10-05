"""Tools the shop agent can call. All product data comes from data/campus_customs.db,
so the agent can only talk about products (and prices, stock, descriptions) that exist.

Tools given to the agent:
- search_products:  find products by keywords and filters
- get_product_info: description, colors, type, and price for one product
- get_price:        price for one product
- check_stock:      how many are in stock, by size, with a clear status per size

Customer-memory and page-context tools (they read RunContext.deps):
- get_current_page_product: the product on the page the shopper is viewing
- find_similar_products:    other items like a product, e.g. "another one in pink"
- recall_past_chats:        search a logged-in shopper's earlier saved conversations

Safety:
- request_human_review:     file a report for a person after 3 failed attempts
"""

import json
import re
import sqlite3
from pathlib import Path

from pydantic_ai import RunContext

from db import get_db
from models import (
    ChatDeps,
    CurrentPageProduct,
    PastChats,
    PriceInfo,
    ProductBrief,
    ProductCard,
    ProductMatch,
    ProductInfo,
    ProductNotFound,
    ProductSearchResult,
    ProductSuggestion,
    SizeAvailability,
    SimilarProducts,
    SizeStock,
    StockInfo,
    StockStatus,
)

SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL"]
MAX_RESULTS = 12
LOW_STOCK_THRESHOLD = 5

# Words that carry no meaning for matching products.
STOPWORDS = {
    "a", "an", "and", "any", "do", "for", "have", "i", "in", "is", "it", "me", "my", "of",
    "on", "or", "please", "show", "some", "something", "the", "to", "want", "with", "you",
    "yale", "looking", "need", "get", "like", "would", "can", "shirt",
}

SYNONYMS = {"hoodie": "hood", "tee": "t-shirt", "sweater": "sweat", "1/4": "quarter", "sweatpants": "pants"}

SIZE_ALIASES = {
    "XS": "XS", "EXTRA SMALL": "XS", "X-SMALL": "XS", "XSMALL": "XS",
    "S": "S", "SMALL": "S",
    "M": "M", "MEDIUM": "M", "MED": "M",
    "L": "L", "LARGE": "L",
    "XL": "XL", "EXTRA LARGE": "XL", "X-LARGE": "XL", "XLARGE": "XL",
    "XXL": "XXL", "2XL": "XXL", "XX-LARGE": "XXL", "XXLARGE": "XXL", "DOUBLE XL": "XXL",
}


# ---------- Helpers ----------


def _image_url(image_file_path: str) -> str:
    return "/images/" + Path(image_file_path).name


def _product_url(product_id: str) -> str:
    return f"/products/{product_id}"


def normalize_size(size: str | None) -> str | None:
    """Map "small", "2xl", "x-large", etc. to XS/S/M/L/XL/XXL. Returns None if unrecognized."""
    if not size:
        return None
    return SIZE_ALIASES.get(re.sub(r"\s+", " ", size.strip().upper()))


def stock_status(quantity: int) -> StockStatus:
    if quantity <= 0:
        return "out_of_stock"
    if quantity <= LOW_STOCK_THRESHOLD:
        return "low_stock"
    return "in_stock"


def _stock_for(conn: sqlite3.Connection, product_ids: list[str]) -> dict[str, list[SizeStock]]:
    if not product_ids:
        return {}
    marks = ",".join("?" * len(product_ids))
    rows = conn.execute(
        f"SELECT product_id, size, quantity FROM inventory WHERE product_id IN ({marks})", product_ids
    ).fetchall()
    stock: dict[str, list[SizeStock]] = {pid: [] for pid in product_ids}
    for r in rows:
        stock[r["product_id"]].append(SizeStock(size=r["size"], quantity=r["quantity"]))
    for sizes in stock.values():
        sizes.sort(key=lambda s: SIZE_ORDER.index(s.size) if s.size in SIZE_ORDER else len(SIZE_ORDER))
    return stock


def _query_terms(query: str) -> list[str]:
    q = re.sub(r"\bt[\s-]?shirts?\b|\btees?\b", "t-shirt", query.lower())
    terms = []
    for t in re.findall(r"[a-z0-9]+(?:[-/][a-z0-9]+)*", q):
        if t in STOPWORDS or len(t) < 2:
            continue
        # Crude plural handling: "hoodies" -> "hoodie", "crewnecks" -> "crewneck".
        if len(t) > 3 and t.endswith("ies"):
            t = t[:-3] + "ie"
        elif len(t) > 3 and t.endswith("s") and not t.endswith("ss"):
            t = t[:-1]
        terms.append(SYNONYMS.get(t, t))
    return terms


def _score(row: sqlite3.Row, terms: list[str]) -> int:
    name = row["name"].lower()
    garment = row["garment_type"].lower()
    tags = row["search_tags"].lower()
    colors = row["colors"].lower()
    desc = row["description"].lower()
    score = 0
    for t in terms:
        if t in name:
            score += 5
        if t in garment:
            score += 4
        if t in colors:
            score += 3
        if t in tags:
            score += 2
        if t in desc:
            score += 1
    return score


def _ranked(rows: list[sqlite3.Row], query: str) -> list[tuple[int, sqlite3.Row]]:
    terms = _query_terms(query)
    if not terms:
        return [(0, r) for r in sorted(rows, key=lambda r: r["name"])]
    scored = [(s, r) for r in rows if (s := _score(r, terms)) > 0]
    scored.sort(key=lambda x: (-x[0], x[1]["name"]))
    return scored


def _resolve(conn: sqlite3.Connection, product: str) -> sqlite3.Row | ProductNotFound:
    """Find one catalogue row from an exact id, an exact name, or the single best keyword match."""
    key = product.strip()
    row = conn.execute("SELECT * FROM catalogue WHERE product_id = ?", (key,)).fetchone()
    if row is None:
        row = conn.execute("SELECT * FROM catalogue WHERE lower(name) = lower(?)", (key,)).fetchone()
    if row is not None:
        return row

    ranked = _ranked(conn.execute("SELECT * FROM catalogue").fetchall(), key)
    # Accept the top match only when it clearly beats the runner-up; otherwise ask the model to pick.
    if ranked and ranked[0][0] > 0 and (len(ranked) == 1 or ranked[0][0] > ranked[1][0]):
        return ranked[0][1]
    return ProductNotFound(
        message=(
            f"No single product matches '{product}'. Ask the shopper which one they mean, "
            "or call again with one of these exact ids."
            if ranked
            else f"No product matches '{product}'. Don't guess; tell the shopper it isn't in the catalogue."
        ),
        suggestions=[ProductSuggestion(id=r["product_id"], name=r["name"]) for _, r in ranked[:5]],
    )


def _to_search_result(row: sqlite3.Row, sizes: list[SizeStock]) -> ProductSearchResult:
    in_stock_sizes = [s.size for s in sizes if s.quantity > 0]
    return ProductSearchResult(
        id=row["product_id"],
        name=row["name"],
        garment_type=row["garment_type"],
        price=row["price"],
        colors=json.loads(row["colors"]),
        description=row["description"],
        image_url=_image_url(row["image_file_path"]),
        product_url=_product_url(row["product_id"]),
        in_stock=bool(in_stock_sizes),
        sizes_in_stock=in_stock_sizes,
        stock_by_size=sizes,
    )


# ---------- Agent tools ----------


def search_products(
    query: str = "",
    color: str | None = None,
    size: str | None = None,
    max_price: float | None = None,
    min_price: float | None = None,
    in_stock_only: bool = False,
    limit: int = 6,
) -> list[ProductBrief]:
    """Search the Campus Customs catalogue and return real products with live price and stock.

    Use this to find products to recommend. Only recommend products it returns, and use its
    prices, descriptions, and stock exactly as given.

    Args:
        query: Keywords like "navy hoodie", "baseball", "Saybrook", "dad", "quarter zip". Empty returns everything.
        color: Only products that include this color, e.g. "gray" or "navy".
        size: Only products with this size in stock: XS, S, M, L, XL, or XXL.
        max_price: Only products at or below this price in USD.
        min_price: Only products at or above this price in USD.
        in_stock_only: If true, skip products that are sold out in every size.
        limit: Maximum number of products to return (1-12).
    """
    limit = max(1, min(limit, MAX_RESULTS))
    return [brief(p) for p in _search(query, color, size, max_price, min_price, in_stock_only)[:limit]]


def brief(p: ProductSearchResult) -> ProductBrief:
    """Only the fields the model needs; cards and links are built by the server."""
    return ProductBrief(
        id=p.id,
        name=p.name,
        garment_type=p.garment_type,
        price=p.price,
        colors=p.colors,
        short_description=_short_description(p.description),
        in_stock=p.in_stock,
        sizes_in_stock=p.sizes_in_stock,
    )


def _search(
    query: str = "",
    color: str | None = None,
    size: str | None = None,
    max_price: float | None = None,
    min_price: float | None = None,
    in_stock_only: bool = False,
) -> list[ProductSearchResult]:
    size = normalize_size(size) if size else None

    with get_db() as conn:
        rows = conn.execute("SELECT * FROM catalogue").fetchall()
        if color:
            rows = [r for r in rows if color.lower() in r["colors"].lower()]
        if max_price is not None:
            rows = [r for r in rows if r["price"] <= max_price]
        if min_price is not None:
            rows = [r for r in rows if r["price"] >= min_price]
        rows = [r for _, r in _ranked(rows, query)]
        stock = _stock_for(conn, [r["product_id"] for r in rows])

    results = [_to_search_result(r, stock[r["product_id"]]) for r in rows]
    if size:
        results = [p for p in results if size in p.sizes_in_stock]
    if in_stock_only:
        results = [p for p in results if p.in_stock]
    return results


def get_product_info(product: str) -> ProductInfo | ProductNotFound:
    """Get the full description, colors, garment type, price, and overall stock for ONE product.

    Call this when the shopper asks what a product is like, what it's made of, what colors
    it comes in, or anything about its description.

    Args:
        product: The product's exact id (preferred, from search_products) or its exact name.
    """
    with get_db() as conn:
        row = _resolve(conn, product)
        if isinstance(row, ProductNotFound):
            return row
        sizes = _stock_for(conn, [row["product_id"]])[row["product_id"]]
    total = sum(s.quantity for s in sizes)
    return ProductInfo(
        id=row["product_id"],
        name=row["name"],
        garment_type=row["garment_type"],
        description=row["description"],
        colors=json.loads(row["colors"]),
        price=row["price"],
        image_url=_image_url(row["image_file_path"]),
        product_url=_product_url(row["product_id"]),
        in_stock=total > 0,
        total_in_stock=total,
    )


def get_price(product: str) -> PriceInfo | ProductNotFound:
    """Get the current price (USD) of ONE product. Always call this before stating a price.

    Args:
        product: The product's exact id (preferred, from search_products) or its exact name.
    """
    with get_db() as conn:
        row = _resolve(conn, product)
    if isinstance(row, ProductNotFound):
        return row
    return PriceInfo(
        id=row["product_id"],
        name=row["name"],
        price=row["price"],
        product_url=_product_url(row["product_id"]),
    )


def check_stock(product: str, size: str | None = None) -> StockInfo | ProductNotFound | str:
    """Check how many of ONE product are in stock, in total and for every size.

    Always call this before answering any question about availability or quantity.
    Each size has a status: "in_stock", "low_stock" (5 or fewer left), or "out_of_stock".
    If the requested size is out of stock, tell the shopper clearly that it is OUT OF STOCK.

    Args:
        product: The product's exact id (preferred, from search_products) or its exact name.
        size: Optional size the shopper asked about: XS, S, M, L, XL, or XXL ("small", "2XL" etc. also work).
    """
    requested = normalize_size(size) if size else None
    if size and requested is None:
        return f"'{size}' isn't a size we carry. Sizes are: {', '.join(SIZE_ORDER)}."

    with get_db() as conn:
        row = _resolve(conn, product)
        if isinstance(row, ProductNotFound):
            return row
        sizes = _stock_for(conn, [row["product_id"]])[row["product_id"]]

    availability = [SizeAvailability(size=s.size, quantity=s.quantity, status=stock_status(s.quantity)) for s in sizes]
    total = sum(s.quantity for s in sizes)
    requested_row = next((a for a in availability if a.size == requested), None)

    out = [a.size for a in availability if a.status == "out_of_stock"]
    low = [f"{a.size} ({a.quantity} left)" for a in availability if a.status == "low_stock"]
    if total == 0:
        summary = "OUT OF STOCK in every size."
    else:
        parts = [f"{total} in stock in total."]
        if out:
            parts.append(f"OUT OF STOCK in {', '.join(out)}.")
        if low:
            parts.append(f"Low stock: {', '.join(low)}.")
        summary = " ".join(parts)
    if requested_row:
        label = {"in_stock": "in stock", "low_stock": "low stock", "out_of_stock": "OUT OF STOCK"}[requested_row.status]
        summary = f"Size {requested}: {label} ({requested_row.quantity} available). " + summary

    return StockInfo(
        id=row["product_id"],
        name=row["name"],
        product_url=_product_url(row["product_id"]),
        requested_size=requested,
        requested_size_quantity=requested_row.quantity if requested_row else None,
        requested_size_status=requested_row.status if requested_row else None,
        sizes=availability,
        total_in_stock=total,
        status="out_of_stock" if total == 0 else ("low_stock" if total <= LOW_STOCK_THRESHOLD else "in_stock"),
        summary=summary,
    )


# ---------- Customer memory and page context ----------


def category_of(garment_type: str) -> str:
    """Group the free-text garment_type into shop categories (same rules as the website)."""
    t = garment_type.lower()
    if "t-shirt" in t:
        return "T-Shirts"
    if "hood" in t:
        return "Hoodies"
    if "quarter-zip" in t:
        return "Quarter-Zips"
    if "jacket" in t:
        return "Jackets"
    if "long-sleeve" in t:
        return "Long Sleeve"
    return "Crewnecks"


def get_current_page_product(ctx: RunContext[ChatDeps]) -> CurrentPageProduct:
    """Get the product the shopper is looking at right now (if they're on a product page).

    Call this whenever the shopper says "this", "it", "this one", or asks about a product
    without naming it, e.g. "do you have this in pink?" or "how much is it?".
    """
    page = ctx.deps.page
    if not page or not page.product_id:
        return CurrentPageProduct(
            on_product_page=False,
            note="The shopper isn't on a product page. Ask which product they mean (or use earlier chat context).",
        )
    info = get_product_info(page.product_id)
    if isinstance(info, ProductNotFound):
        return CurrentPageProduct(on_product_page=False, note="The page's product wasn't found in the catalogue.")
    stock = check_stock(info.id)
    return CurrentPageProduct(
        on_product_page=True,
        product=info,
        selected_size=normalize_size(page.selected_size),
        sizes=stock.sizes if isinstance(stock, StockInfo) else [],
    )


def find_similar_products(
    ctx: RunContext[ChatDeps],
    product: str | None = None,
    color: str | None = None,
    max_price: float | None = None,
    in_stock_only: bool = True,
    limit: int = 6,
) -> SimilarProducts | ProductNotFound:
    """Find other products similar to one product: same category (hoodie, crewneck, T-shirt...),
    optionally in a different color or under a price.

    Use this for "do you have another one in pink?", "anything like this but cheaper?",
    or "what else is similar?". Leave `product` empty to use the product on the current page.

    Args:
        product: Exact id or name of the product to compare against. Empty = the current page's product.
        color: Only include products that come in this color, e.g. "pink".
        max_price: Only include products at or below this price in USD.
        in_stock_only: Skip products that are sold out in every size.
        limit: Maximum number of products to return (1-12).
    """
    product = product or (ctx.deps.page.product_id if ctx.deps.page else None)
    if not product:
        return ProductNotFound(message="No product given and the shopper isn't on a product page. Ask which product they mean.")
    with get_db() as conn:
        base = _resolve(conn, product)
    if isinstance(base, ProductNotFound):
        return base

    category = category_of(base["garment_type"])
    candidates = [
        p
        for p in _search(color=color, max_price=max_price, in_stock_only=in_stock_only)
        if p.id != base["product_id"] and category_of(p.garment_type) == category
    ]
    note = ""
    if not candidates and color:
        # Nothing in that category and color: say so, and offer that color in other categories.
        candidates = [p for p in _search(color=color, max_price=max_price, in_stock_only=in_stock_only) if p.id != base["product_id"]]
        note = (
            f"No other {category.lower()} come in {color}. "
            + (f"These other items do come in {color}." if candidates else f"Nothing in the catalogue comes in {color}.")
        )
    return SimilarProducts(
        based_on_id=base["product_id"],
        based_on_name=base["name"],
        category=category,
        color=color,
        results=[brief(p) for p in candidates[: max(1, min(limit, MAX_RESULTS))]],
        note=note,
    )


def recall_past_chats(ctx: RunContext[ChatDeps], query: str = "", limit: int = 8) -> PastChats:
    """Search this shopper's earlier saved conversations (logged-in shoppers only).

    Use when they refer to something from a previous visit, e.g. "what was that hoodie you
    showed me last time?" or "did I ask about sizes before?". Recent messages are already in
    the conversation; this finds older ones.

    Args:
        query: A word to look for, e.g. "hoodie" or "Saybrook". Empty = most recent messages.
        limit: Maximum number of messages to return (1-20).
    """
    from memory import search_past_chats  # imported here to avoid a circular import

    user = ctx.deps.user
    if not user:
        return PastChats(logged_in=False, note="The shopper is a guest, so there's no saved chat history.")
    messages = search_past_chats(user["id"], query, limit)
    return PastChats(
        logged_in=True,
        messages=messages,
        note="" if messages else "No earlier messages matched.",
    )


# ---------- Safety: hand off to a human ----------


def request_human_review(ctx: RunContext[ChatDeps], reason: str, what_was_tried: str) -> str:
    """File a report for a Campus Customs team member, then stop trying.

    Call this after 3 failed attempts at the shopper's request (lookups that found nothing,
    rejected answers, or errors), or when a request needs a person (order problems, refunds,
    complaints). Then tell the shopper the team will follow up. Do not include passwords,
    payment details, or other sensitive data in the report.

    Args:
        reason: One sentence on why you're handing this off.
        what_was_tried: Short summary of the attempts you made.
    """
    from audit import file_human_review  # imported here to keep tools importable on their own

    user = ctx.deps.user
    report_id = file_human_review(
        run_id=ctx.deps.run_id,
        user=f"user:{user['id']}" if user else "guest",
        message=ctx.prompt if isinstance(ctx.prompt, str) else "",
        reason=reason,
        details={"filed_by": "agent", "what_was_tried": what_was_tried},
    )
    ctx.deps.review_ids.append(report_id)
    return f"Report {report_id} filed for the Campus Customs team. Tell the shopper a team member will follow up, and stop trying."


# ---------- Used by the agent's output checks (not given to the model) ----------

PAGE_RESULTS_LIMIT = 48


def _short_description(text: str, limit: int = 110) -> str:
    first = re.split(r"(?<=[.!?])\s", text.strip(), maxsplit=1)[0]
    if len(first) <= limit:
        return first
    return first[: limit - 1].rsplit(" ", 1)[0].rstrip(",;:") + "…"


def page_matches(
    query: str = "",
    color: str | None = None,
    size: str | None = None,
    max_price: float | None = None,
    min_price: float | None = None,
    in_stock_only: bool = False,
) -> tuple[list[ProductMatch], int]:
    """Re-run a search for the website's results grid (more results than the model sees)."""
    results = _search(query, color, size, max_price, min_price, in_stock_only)
    matches = [
        ProductMatch(
            id=p.id,
            name=p.name,
            price=p.price,
            image_url=p.image_url,
            short_description=_short_description(p.description),
            in_stock=p.in_stock,
            product_url=p.product_url,
        )
        for p in results[:PAGE_RESULTS_LIMIT]
    ]
    return matches, len(results)



def card_from_db(product_id: str) -> ProductCard | None:
    """Build a product card from the database (used to overwrite whatever the model wrote)."""
    info = get_product_info(product_id)
    if isinstance(info, ProductNotFound) or info.id != product_id:
        return None
    return ProductCard(
        id=info.id,
        name=info.name,
        price=info.price,
        image_url=info.image_url,
        description=info.description,
        in_stock=info.in_stock,
        product_url=info.product_url,
    )
