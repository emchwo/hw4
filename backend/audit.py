"""Audit trail and human-review reports.

- output/audit_trail.json: one entry per agent run (time, tool calls with short args/results,
  stop reason, reply type, usage). Entries are appended; the file is never erased between runs.
- output/human_review.json: reports for a person to look at when the agent gives up after
  3 failed attempts (or the run fails). Also append-only.

Privacy: shoppers are recorded by user id (or "guest"), never name/email. Text is shortened
and anything that looks like an email, API key, card number, or password is redacted.
"""

import json
import re
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    RetryPromptPart,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
)
from pydantic_core import to_json

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
AUDIT_PATH = OUTPUT_DIR / "audit_trail.json"
REVIEW_PATH = OUTPUT_DIR / "human_review.json"

PREVIEW_CHARS = 200
MAX_FAILED_ATTEMPTS = 3

_lock = threading.Lock()

_REDACTIONS = [
    (re.compile(r"\b(sk|pk|rk)-[A-Za-z0-9_\-]{12,}\b"), "[redacted key]"),
    (re.compile(r"\b[A-Za-z0-9_\-]{32,}\b"), "[redacted token]"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"), "[redacted email]"),
    (re.compile(r"\b(?:\d[ -]?){13,19}\b"), "[redacted number]"),
    (re.compile(r"(?i)(password|passwd|pwd)\s*[:=]?\s*\S+"), r"\1 [redacted]"),
]


def redact(text: str) -> str:
    for pattern, replacement in _REDACTIONS:
        text = pattern.sub(replacement, text)
    return text


def preview(value: Any, limit: int = PREVIEW_CHARS) -> str:
    text = value if isinstance(value, str) else to_json(value).decode("utf-8", "replace")
    text = redact(" ".join(text.split()))
    return text if len(text) <= limit else text[: limit - 1] + "…"


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _is_failed_result(content: Any) -> bool:
    """A tool result that didn't find what was asked for (counts toward the 3-attempt limit)."""
    if isinstance(content, str):
        return content.startswith("No product") or "isn't a size we carry" in content
    found = getattr(content, "found", None)
    if found is False:
        return True
    return isinstance(content, dict) and content.get("found") is False


def summarize_run(messages: list[ModelMessage]) -> dict[str, Any]:
    """Tool calls (name, short args, short result), failed attempts, and the stop reason."""
    calls: list[dict[str, Any]] = []
    by_id: dict[str, dict[str, Any]] = {}
    failed = 0
    finish_reason = None

    for message in messages:
        if isinstance(message, ModelResponse):
            finish_reason = message.finish_reason or finish_reason
            for part in message.parts:
                if isinstance(part, ToolCallPart):
                    entry = {
                        "time": message.timestamp.isoformat(timespec="seconds") if message.timestamp else now(),
                        "tool": part.tool_name,
                        # PydanticAI returns the structured reply through a "final_result_*" output tool.
                        "kind": "output" if part.tool_name.startswith("final_result") else "tool",
                        "args": preview(part.args_as_dict()),
                        "result": None,
                        "ok": True,
                    }
                    calls.append(entry)
                    by_id[part.tool_call_id] = entry
        elif isinstance(message, ModelRequest):
            for part in message.parts:
                if isinstance(part, ToolReturnPart):
                    entry = by_id.get(part.tool_call_id)
                    if entry is not None:
                        entry["result"] = preview(part.content)
                        if _is_failed_result(part.content):
                            entry["ok"] = False
                            failed += 1
                elif isinstance(part, RetryPromptPart):
                    # The model's output or tool call was rejected and it had to try again.
                    failed += 1
                    entry = by_id.get(part.tool_call_id) if part.tool_call_id else None
                    if entry is not None:
                        entry["ok"] = False
                        entry["result"] = "retry: " + preview(part.content)

    return {"tool_calls": calls, "failed_attempts": failed, "finish_reason": finish_reason or "stop"}


def last_text(messages: list[ModelMessage]) -> str:
    for message in reversed(messages):
        if isinstance(message, ModelResponse):
            for part in message.parts:
                if isinstance(part, TextPart) and part.content:
                    return preview(part.content)
    return ""


def _append(path: Path, entry: dict[str, Any]) -> None:
    """Append one entry to a JSON array file without touching earlier entries."""
    with _lock:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        rows: list[Any] = []
        if path.exists() and path.stat().st_size > 0:
            try:
                loaded = json.loads(path.read_text(encoding="utf-8"))
                rows = loaded if isinstance(loaded, list) else [loaded]
            except json.JSONDecodeError:
                # Keep the unreadable file instead of overwriting it.
                stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                path.replace(path.with_name(f"{path.stem}.corrupt-{stamp}.json"))
        rows.append(entry)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(path)


def append_audit(entry: dict[str, Any]) -> None:
    _append(AUDIT_PATH, entry)


def file_human_review(*, run_id: str, user: str, message: str, reason: str, details: dict[str, Any]) -> str:
    """Write a report for a person to look at. Returns the report id."""
    report_id = "HR-" + uuid.uuid4().hex[:8].upper()
    _append(
        REVIEW_PATH,
        {
            "report_id": report_id,
            "time": now(),
            "run_id": run_id,
            "user": user,
            "shopper_message": preview(message, 400),
            "reason": preview(reason, 400),
            "details": details,
            "status": "open",
        },
    )
    return report_id
