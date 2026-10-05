"""Structured types for the shop agent.

The agent's output is a union of reply types. Each has a literal `type` field so
the frontend knows how to render it:
- "text": a plain text answer
    - "price": a text answer about one product's price (subtype of TextReply)
    - "stock": a text answer about one product's stock (subtype of TextReply)
- "product_search": catalogue search results that the website shows on the Products page
- "product_recommendation": a short message plus product cards
- "clarifying_question": a question back to the shopper (with optional quick replies)

Price and stock replies only ask the model for a product id (and size). The real
numbers are looked up from the database by the server and attached in fields the
model never sees, so prices and quantities can't be hallucinated.
"""

from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field
from pydantic.json_schema import SkipJsonSchema

StockStatus = Literal["in_stock", "low_stock", "out_of_stock"]


# ---------- Tool results (real rows from the database) ----------


class SizeStock(BaseModel):
    size: str
    quantity: int


class SizeAvailability(BaseModel):
    size: str
    quantity: int
    status: StockStatus


class ProductSearchResult(BaseModel):
    """Returned by search_products."""

    id: str
    name: str
    garment_type: str
    price: float
    currency: Literal["USD"] = "USD"
    colors: list[str]
    description: str
    image_url: str
    product_url: str
    in_stock: bool
    sizes_in_stock: list[str]
    stock_by_size: list[SizeStock]


class ProductBrief(BaseModel):
    """Compact product row sent to the model by search tools (no image/link/per-size counts)."""

    id: str
    name: str
    garment_type: str
    price: float
    colors: list[str]
    short_description: str
    in_stock: bool
    sizes_in_stock: list[str]


class ProductInfo(BaseModel):
    """Returned by get_product_info: everything describing one product."""

    id: str
    name: str
    garment_type: str
    description: str
    colors: list[str]
    price: float
    currency: Literal["USD"] = "USD"
    image_url: str
    product_url: str
    in_stock: bool
    total_in_stock: int


class PriceInfo(BaseModel):
    """Returned by get_price."""

    id: str
    name: str
    price: float
    currency: Literal["USD"] = "USD"
    product_url: str


class StockInfo(BaseModel):
    """Returned by check_stock: quantity and status for every size."""

    id: str
    name: str
    product_url: str
    requested_size: str | None = None
    requested_size_quantity: int | None = None
    requested_size_status: StockStatus | None = None
    sizes: list[SizeAvailability]
    total_in_stock: int
    status: StockStatus
    summary: str = Field(description="Plain-English stock summary; out-of-stock sizes are written in capitals.")


class ProductSuggestion(BaseModel):
    id: str
    name: str


class ProductNotFound(BaseModel):
    """Returned when a lookup doesn't match exactly one product."""

    found: Literal[False] = False
    message: str
    suggestions: list[ProductSuggestion] = Field(default_factory=list)


# ---------- Agent replies ----------


class ProductCard(BaseModel):
    """A product the agent recommends. Fields are overwritten from the database before
    the reply is sent, so prices and descriptions always match the real catalogue."""

    id: str = Field(description="product_id exactly as returned by the search_products tool")
    name: str
    price: float
    currency: Literal["USD"] = "USD"
    image_url: str
    description: str
    in_stock: bool
    product_url: str


class TextReply(BaseModel):
    """A plain text reply: greetings, general questions, store info, or declining a request."""

    type: Literal["text"] = "text"
    message: str = Field(description="The reply to show the shopper.")


class PriceReply(TextReply):
    """Answer a question about ONE product's price. Call get_price first."""

    type: Literal["price"] = "price"  # type: ignore[assignment]
    message: str = Field(description="Short answer that states the price exactly as get_price returned it.")
    product_id: str = Field(description="Exact product id from get_price.")
    # Filled in by the server from the database; hidden from the model.
    price_info: SkipJsonSchema[PriceInfo | None] = None


class StockReply(TextReply):
    """Answer a question about ONE product's stock or size availability. Call check_stock first."""

    type: Literal["stock"] = "stock"  # type: ignore[assignment]
    message: str = Field(
        description="Short answer using check_stock's numbers. If the size asked about is out of stock, say 'out of stock' clearly."
    )
    product_id: str = Field(description="Exact product id from check_stock.")
    size: str | None = Field(default=None, description="The size the shopper asked about, if any.")
    # Filled in by the server from the database; hidden from the model.
    stock_info: SkipJsonSchema[StockInfo | None] = None


class ProductMatch(BaseModel):
    """One search result card shown on the page. Always built from the database."""

    id: str
    name: str
    price: float
    currency: Literal["USD"] = "USD"
    image_url: str
    short_description: str
    in_stock: bool
    product_url: str


class SearchFilters(BaseModel):
    """The search the agent ran. The server re-runs it to build the matches."""

    query: str = Field(default="", description="Keywords passed to search_products, e.g. 'hoodie' or 'navy crewneck'.")
    color: str | None = None
    size: str | None = None
    max_price: float | None = None
    min_price: float | None = None
    in_stock_only: bool = False


class ProductSearchReply(BaseModel):
    """Show catalogue search results on the page when the shopper asks whether the store has a
    kind of product ("do you have hoodies?", "show me gray t-shirts under $40"). Call search_products first."""

    type: Literal["product_search"] = "product_search"
    message: str = Field(description="One short sentence, e.g. 'Yes! Here are our hoodies.' Don't list products or prices.")
    search: SearchFilters = Field(description="The same arguments you passed to search_products.")
    label: str = Field(description="Short heading for the results, e.g. 'Hoodies' or 'Gray T-shirts under $40'.")
    # Filled in by the server from the database; hidden from the model.
    matches: SkipJsonSchema[list[ProductMatch]] = Field(default_factory=list)
    total_matches: SkipJsonSchema[int] = 0


class ProductRecommendationReply(BaseModel):
    """Recommend specific products that were returned by a tool (search_products, find_similar_products...)."""

    type: Literal["product_recommendation"] = "product_recommendation"
    message: str = Field(description="One or two short sentences introducing the products.")
    product_ids: list[str] = Field(min_length=1, max_length=6, description="Exact ids of the products to show.")
    # Cards are built by the server from the database; hidden from the model (saves output tokens).
    products: SkipJsonSchema[list[ProductCard]] = Field(default_factory=list)


class ClarifyingQuestionReply(BaseModel):
    """Ask the shopper for more information before searching or recommending."""

    type: Literal["clarifying_question"] = "clarifying_question"
    question: str = Field(description="One short, specific question.")
    options: list[str] = Field(
        default_factory=list,
        max_length=5,
        description="Optional short answers the shopper can tap, e.g. ['Hoodie', 'Crewneck'].",
    )


AgentReply = (
    TextReply | PriceReply | StockReply | ProductSearchReply | ProductRecommendationReply | ClarifyingQuestionReply
)

REPLY_TYPES = [TextReply, PriceReply, StockReply, ProductSearchReply, ProductRecommendationReply, ClarifyingQuestionReply]


# ---------- API request / response ----------


class ChatHistoryItem(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)


class PageContext(BaseModel):
    """What the shopper is looking at, sent by the website with each message.
    Only ids are trusted; the server looks up names, colors, etc. from the database."""

    path: str = Field(default="/", max_length=200)
    product_id: str | None = Field(default=None, max_length=200, description="Set on a single-item page.")
    selected_size: str | None = Field(default=None, max_length=10)
    category: str | None = Field(default=None, max_length=50)
    search_label: str | None = Field(default=None, max_length=120, description="Heading of chat results on the page.")
    visible_product_ids: list[str] = Field(default_factory=list, max_length=60)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    # Only used for guests; logged-in shoppers' history is loaded from the database.
    history: list[ChatHistoryItem] = Field(default_factory=list, max_length=40)
    page: PageContext | None = None


class ChatResponse(BaseModel):
    type: Literal["text", "price", "stock", "product_search", "product_recommendation", "clarifying_question"]
    reply: str
    search_label: str | None = None
    matches: list[ProductMatch] = Field(default_factory=list)
    total_matches: int = 0
    products: list[ProductCard] = Field(default_factory=list)
    options: list[str] = Field(default_factory=list)
    price: PriceInfo | None = None
    stock: StockInfo | None = None


class HistoryMessage(BaseModel):
    """One saved chat message for a logged-in shopper."""

    id: int
    role: Literal["user", "assistant"]
    content: str
    created_at: str
    # The structured reply (cards, matches, options...) for assistant messages.
    reply: ChatResponse | None = None


class ChatHistoryResponse(BaseModel):
    messages: list[HistoryMessage]


# ---------- Memory / page-context tool results ----------


class CurrentPageProduct(BaseModel):
    """Returned by get_current_page_product."""

    on_product_page: bool
    product: ProductInfo | None = None
    selected_size: str | None = None
    sizes: list[SizeAvailability] = Field(default_factory=list)
    note: str = ""


class SimilarProducts(BaseModel):
    """Returned by find_similar_products."""

    based_on_id: str
    based_on_name: str
    category: str
    color: str | None = None
    results: list[ProductBrief]
    note: str = ""


class PastChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    created_at: str
    products_shown: list[str] = Field(default_factory=list)


class PastChats(BaseModel):
    """Returned by recall_past_chats."""

    logged_in: bool
    messages: list[PastChatMessage] = Field(default_factory=list)
    note: str = ""


# ---------- Per-request context for the agent ----------


@dataclass
class ChatDeps:
    """Who the shopper is and what page they're on, passed to tools via RunContext."""

    user: dict | None = None  # id, name, first_name, last_name, email (None for guests)
    page: PageContext | None = None
    run_id: str = ""  # links this run's audit-trail entry and any human-review report
    review_ids: list[str] = field(default_factory=list)  # reports filed during this run
