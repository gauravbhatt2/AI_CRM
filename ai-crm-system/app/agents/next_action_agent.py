"""
Next Best Action — rules first, short Groq fallback when signals are ambiguous.
"""

from __future__ import annotations

import re
from typing import Any

from app.agents._groq_text import groq_text_or_none

_VALID_INTENT = frozenset({"high", "medium", "low"})
_VALID_RISK = frozenset({"low", "medium", "high"})


def _norm_intent(record: dict[str, Any]) -> str:
    s = str(record.get("intent", "")).strip().lower()
    return s if s in _VALID_INTENT else ""


def _norm_risk(record: dict[str, Any]) -> str:
    s = str(record.get("risk_level", "")).strip().lower()
    return s if s in _VALID_RISK else ""


def _timeline_near(record: dict[str, Any]) -> bool:
    tl = str(record.get("timeline", "")).strip().lower()
    if not tl or tl in ("n/a", "na", "none", "unknown"):
        return False
    hints = (
        "asap",
        "urgent",
        "this week",
        "today",
        "tomorrow",
        "immediate",
        "eom",
        "end of month",
        "eoy",
        "end of year",
        "next few days",
        "within a week",
        "shortly",
        "right away",
    )
    return any(h in tl for h in hints) or bool(re.search(r"\b\d{1,2}\s*(day|week)s?\b", tl))


def _rule_next_action(record: dict[str, Any]) -> str | None:
    intent = _norm_intent(record)
    risk = _norm_risk(record)

    if risk == "high":
        return "Address concerns before proceeding"

    if _timeline_near(record):
        return "Prioritize follow-up immediately"

    if intent == "high" and risk == "low":
        return "Send pricing and close deal"

    if intent == "medium":
        return "Schedule demo with customer"

    # Clear cases handled; ambiguous (e.g. high intent + medium risk, or missing labels)
    if not intent or not risk:
        return None
    if intent == "high" and risk == "medium":
        return None
    if intent == "low":
        return None
    return None


def _truncate_words(text: str, max_words: int = 10) -> str:
    words = text.replace("\n", " ").split()
    if len(words) <= max_words:
        return " ".join(words).strip()
    return " ".join(words[:max_words]).strip()


def suggest_next_action(record: dict[str, Any]) -> str:
    ruled = _rule_next_action(record)
    if ruled:
        return _truncate_words(ruled, 10)

    compact = {
        "intent": record.get("intent"),
        "risk_level": record.get("risk_level"),
        "timeline": record.get("timeline"),
        "product": record.get("product"),
        "next_step": record.get("next_step"),
        "summary": (str(record.get("summary", "") or "")[:400]),
    }
    prompt = (
        "You are a sales assistant. Output ONE short imperative next step for the rep.\n"
        "Rules: max 10 words. Actionable. No explanation, no quotes, no punctuation at end.\n"
        f"Context JSON: {compact!r}\n"
        "Next step:"
    )
    out = groq_text_or_none(prompt, max_tokens=48, temperature=0.1)
    if out:
        line = out.splitlines()[0].strip().strip('"').strip("'")
        return _truncate_words(line, 10) or "Follow up with the contact"
    return "Follow up with the contact"
