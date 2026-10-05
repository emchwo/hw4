"""Campus Customs shop agent: PydanticAI agent called through Portkey.

The agent's output type is a union of reply types (see models.py). Before a reply
is returned, product cards, prices, and stock are checked against the database, so
the agent can't show products that don't exist or made-up prices/quantities.

Every run is appended to output/audit_trail.json. After 3 failed attempts in one run the
lookup tools are withdrawn, the agent must hand off with request_human_review, and if a run
fails outright a report is filed in output/human_review.json automatically.
"""

import asyncio
import logging
import os
import re
import time
import uuid
from functools import lru_cache
from pathlib import Path

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

from dotenv import load_dotenv  # noqa: E402
from openai import AsyncOpenAI  # noqa: E402
from pydantic_ai import Agent, ModelRetry, RunContext, Tool, capture_run_messages  # noqa: E402
from pydantic_ai.exceptions import UnexpectedModelBehavior, UsageLimitExceeded  # noqa: E402
from pydantic_ai.tools import ToolDefinition  # noqa: E402
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, TextPart, UserPromptPart  # noqa: E402
from pydantic_ai.models.openai import OpenAIChatModel, OpenAIChatModelSettings  # noqa: E402
from pydantic_ai.providers.openai import OpenAIProvider  # noqa: E402
from pydantic_ai.usage import UsageLimits  # noqa: E402

from models import (  # noqa: E402
    REPLY_TYPES,
    AgentReply,
    ChatDeps,
    ChatHistoryItem,
    ProductInfo,
    PriceInfo,
    PriceReply,
    ProductRecommendationReply,
    ProductSearchReply,
    StockInfo,
    StockReply,
)
from audit import (  # noqa: E402
    MAX_FAILED_ATTEMPTS,
    append_audit,
    file_human_review,
    last_text,
    now,
    preview,
    summarize_run,
)
from tools import (  # noqa: E402
    card_from_db,
    check_stock,
    find_similar_products,
    get_current_page_product,
    get_price,
    get_product_info,
    page_matches,
    recall_past_chats,
    request_human_review,
    search_products,
)

HERE = Path(__file__).resolve().parent
load_dotenv(HERE.parent / ".env")
load_dotenv(HERE.parent.parent / ".env")

# The course Portkey key routes every request to gpt-5.6-luna, so name it honestly here.
# Set AGENT_MODEL to try another model if the key's routing changes.
MODEL_NAME = os.getenv("AGENT_MODEL", "gpt-5.6-luna")
PORTKEY_BASE_URL = os.getenv("PORTKEY_BASE_URL", "https://api.portkey.ai/v1").rstrip("/")
PROMPT_PATH = HERE / "prompts" / "prompt.md"

# Shopping questions are simple lookups, so no extra reasoning: faster and cheaper.
# (gpt-5.6-luna on /chat/completions only allows "none" when function tools are attached.)
REASONING_EFFORT = os.getenv("AGENT_REASONING_EFFORT", "none")

AGENT_TIMEOUT_SECONDS = 60
MAX_MODEL_REQUESTS = 10

log = logging.getLogger("campus_customs.agent")


class AgentConfigError(RuntimeError):
    """The agent can't run because configuration (e.g. the API key) is missing."""


class AgentGaveUp(RuntimeError):
    """The agent stopped after repeated failures; a human-review report was filed."""

    def __init__(self, report_id: str):
        super().__init__(f"Handed off to a human (report {report_id}).")
        self.report_id = report_id


def _gave_up(ctx: RunContext[ChatDeps]) -> bool:
    return summarize_run(ctx.messages)["failed_attempts"] >= MAX_FAILED_ATTEMPTS


async def _hide_after_failures(ctx: RunContext[ChatDeps], tool_def: ToolDefinition) -> ToolDefinition | None:
    """Safety rule: after 3 failed attempts, stop offering lookup tools so the agent hands off."""
    return None if _gave_up(ctx) else tool_def


@lru_cache(maxsize=1)
def get_agent() -> Agent[ChatDeps, AgentReply]:
    api_key = os.getenv("PORTKEY_API_KEY", "").strip()
    if not api_key:
        raise AgentConfigError("PORTKEY_API_KEY is not set.")

    client = AsyncOpenAI(
        api_key=api_key,
        base_url=PORTKEY_BASE_URL,
        default_headers={"x-portkey-api-key": api_key},
    )
    model = OpenAIChatModel(MODEL_NAME, provider=OpenAIProvider(openai_client=client))

    agent: Agent[ChatDeps, AgentReply] = Agent(
        model,
        deps_type=ChatDeps,
        output_type=REPLY_TYPES,
        instructions=PROMPT_PATH.read_text(encoding="utf-8"),
        tools=[
            *(
                Tool(fn, prepare=_hide_after_failures)
                for fn in (
                    search_products,
                    get_product_info,
                    get_price,
                    check_stock,
                    get_current_page_product,
                    find_similar_products,
                    recall_past_chats,
                )
            ),
            request_human_review,
        ],
        # 1 try + 2 retries = 3 attempts at a valid answer before the run fails.
        retries=MAX_FAILED_ATTEMPTS - 1,
        model_settings=OpenAIChatModelSettings(
            openai_reasoning_effort=REASONING_EFFORT,
            parallel_tool_calls=True,  # e.g. check price and stock in one round trip
        ),
    )

    @agent.instructions
    def shopper_and_page(ctx: RunContext[ChatDeps]) -> str:
        text = describe_context(ctx.deps)
        if _gave_up(ctx):
            text += (
                "\n- **You've had 3 failed attempts on this request. Stop trying:** call "
                "`request_human_review`, then reply with `text` telling the shopper a team member will follow up."
            )
        return text

    @agent.output_validator
    def ground_in_database(ctx: RunContext[ChatDeps], reply: AgentReply) -> AgentReply:
        """Attach real database values to replies; ask the model to retry if it got facts wrong."""
        if isinstance(reply, PriceReply):
            return _ground_price(reply)
        if isinstance(reply, StockReply):
            return _ground_stock(reply)
        if isinstance(reply, ProductSearchReply):
            reply.matches, reply.total_matches = page_matches(**reply.search.model_dump())
            if reply.total_matches == 0:
                raise ModelRetry(
                    "That search matches no products. Reply with a text message saying we don't carry it, "
                    "and suggest something we do have."
                )
            return reply
        if not isinstance(reply, ProductRecommendationReply):
            return reply
        cards, seen = [], set()
        for pid in reply.product_ids:
            if pid in seen:
                continue
            real = card_from_db(pid)
            if real is None:
                raise ModelRetry(
                    f"Product id '{pid}' does not exist. Only recommend products returned by a tool, "
                    "using their exact ids."
                )
            cards.append(real)
            seen.add(pid)
        reply.products = cards
        return reply

    return agent


def describe_context(deps: ChatDeps) -> str:
    """Per-request instructions: who the shopper is and what they're looking at."""
    lines = ["## This conversation"]
    user = deps.user
    if user:
        name = user.get("name") or " ".join(filter(None, [user.get("first_name"), user.get("last_name")]))
        lines.append(
            f"- You're chatting with **{name}** (first name: {user.get('first_name') or name}), "
            f"email {user['email']}. They're logged in, so this chat is saved to their account."
        )
    else:
        lines.append("- The shopper is a **guest** (not logged in). You don't know their name or email; don't ask for them.")

    page = deps.page
    if page:
        info = get_product_info(page.product_id) if page.product_id else None
        if isinstance(info, ProductInfo):
            size = f" They've selected size {page.selected_size}." if page.selected_size else ""
            lines.append(
                f"- They're viewing the product page for **{info.name}** (id `{info.id}`): {info.garment_type}, "
                f"colors {', '.join(info.colors)}.{size} If they say \"this\", \"it\", or \"this one\", they mean this product."
            )
        elif page.search_label:
            lines.append(f"- They're on the Products page looking at chat search results: \"{page.search_label}\".")
        elif page.category:
            lines.append(f"- They're on the Products page, filtered to {page.category}.")
        else:
            lines.append(f"- They're on the page `{page.path}`.")
    return "\n".join(lines)


def _mentions_price(message: str, price: float) -> bool:
    """True if the message states the real price, e.g. "$68" or "$68.00"."""
    amounts = re.findall(r"\$\s?(\d+(?:\.\d{1,2})?)", message)
    return any(abs(float(a) - price) < 0.005 for a in amounts)


def _ground_price(reply: PriceReply) -> PriceReply:
    info = get_price(reply.product_id)
    if not isinstance(info, PriceInfo) or info.id != reply.product_id:
        raise ModelRetry(f"'{reply.product_id}' is not an exact product id. Call get_price and use the id it returns.")
    if not _mentions_price(reply.message, info.price):
        raise ModelRetry(f"The price of {info.name} is ${info.price:.2f}. State that exact price in the message.")
    reply.price_info = info
    return reply


def _ground_stock(reply: StockReply) -> StockReply:
    info = check_stock(reply.product_id, reply.size)
    if isinstance(info, str):
        raise ModelRetry(info)
    if not isinstance(info, StockInfo) or info.id != reply.product_id:
        raise ModelRetry(f"'{reply.product_id}' is not an exact product id. Call check_stock and use the id it returns.")
    sold_out = info.requested_size_status == "out_of_stock" or (info.requested_size is None and info.total_in_stock == 0)
    if sold_out and not re.search(r"out of stock|sold out", reply.message, re.IGNORECASE):
        where = f"size {info.requested_size}" if info.requested_size else "every size"
        raise ModelRetry(f"{info.name} is out of stock in {where}. Say clearly that it is out of stock.")
    reply.stock_info = info
    return reply


def _to_model_history(history: list[ChatHistoryItem]) -> list[ModelMessage]:
    messages: list[ModelMessage] = []
    for item in history:
        if item.role == "user":
            messages.append(ModelRequest(parts=[UserPromptPart(content=item.content)]))
        else:
            messages.append(ModelResponse(parts=[TextPart(content=item.content)]))
    return messages


async def run_agent(
    message: str, history: list[ChatHistoryItem] | None = None, deps: ChatDeps | None = None
) -> AgentReply:
    """Run the agent on one shopper message and record it in the audit trail.

    Raises AgentGaveUp (with a human-review report id) if the agent fails repeatedly, and
    re-raises config errors, model errors, and timeouts after recording them.
    """
    agent = get_agent()
    deps = deps or ChatDeps()
    deps.run_id = "run-" + uuid.uuid4().hex[:10]
    user = f"user:{deps.user['id']}" if deps.user else "guest"
    entry: dict = {
        "run_id": deps.run_id,
        "time": now(),
        "user": user,
        "page": deps.page.path if deps.page else None,
        "message": preview(message),
        "model": MODEL_NAME,
    }
    started = time.perf_counter()

    with capture_run_messages() as messages:
        try:
            result = await asyncio.wait_for(
                agent.run(
                    message,
                    deps=deps,
                    message_history=_to_model_history(history or []),
                    usage_limits=UsageLimits(request_limit=MAX_MODEL_REQUESTS),
                ),
                timeout=AGENT_TIMEOUT_SECONDS,
            )
        except Exception as exc:
            run = summarize_run(messages)
            # The attempt that raised UnexpectedModelBehavior never got a retry prompt, so count it here.
            if isinstance(exc, UnexpectedModelBehavior):
                run["failed_attempts"] += 1
            stop = "timeout" if isinstance(exc, asyncio.TimeoutError) else f"error: {type(exc).__name__}"
            report_id = file_human_review(
                run_id=deps.run_id,
                user=user,
                message=message,
                reason=f"Agent run failed ({stop}) after {run['failed_attempts']} failed attempts.",
                details={"filed_by": "server", "error": preview(str(exc)), "tool_calls": run["tool_calls"]},
            )
            entry.update(
                tool_calls=run["tool_calls"],
                failed_attempts=run["failed_attempts"],
                stop_reason=stop,
                reply_type=None,
                reply_preview=last_text(messages),
                human_review=[*deps.review_ids, report_id],
                duration_s=round(time.perf_counter() - started, 2),
            )
            append_audit(entry)
            if isinstance(exc, (UnexpectedModelBehavior, UsageLimitExceeded)):
                raise AgentGaveUp(report_id) from exc
            raise

    run = summarize_run(result.new_messages())
    usage = result.usage
    entry.update(
        tool_calls=run["tool_calls"],
        failed_attempts=run["failed_attempts"],
        stop_reason=(
            "handed off to a human after 3 failed attempts"
            if deps.review_ids
            else f"final answer ({result.output.type}, finish_reason={run['finish_reason']})"
        ),
        reply_type=result.output.type,
        reply_preview=preview(getattr(result.output, "message", None) or getattr(result.output, "question", "")),
        human_review=deps.review_ids,
        model_served=result.response.model_name,
        requests=usage.requests,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        duration_s=round(time.perf_counter() - started, 2),
    )
    append_audit(entry)
    log.info("agent reply type=%s model=%s", result.output.type, result.response.model_name)
    return result.output
