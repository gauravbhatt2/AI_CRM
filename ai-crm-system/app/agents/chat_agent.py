"""
Deal chat — answers from structured CRM fields only (no raw transcript in the LLM context).

Primary: OpenRouter (e.g. Gemma). Fallback: Groq text completion.
"""

from __future__ import annotations

import json
from typing import Any

from app.agents._groq_text import groq_text_or_none
from app.services.chat_model import chat_with_model


def _record_for_prompt(record: dict[str, Any]) -> dict[str, Any]:
    """Narrow payload — excludes raw transcript (`content`) for grounded chat."""
    allow = (
        "budget",
        "intent",
        "competitors",
        "product",
        "product_version",
        "timeline",
        "industry",
        "pain_points",
        "next_step",
        "urgency_reason",
        "stakeholders",
        "mentioned_company",
        "procurement_stage",
        "use_case",
        "decision_criteria",
        "budget_owner",
        "implementation_scope",
        "custom_fields",
        "interaction_type",
        "deal_score",
        "risk_level",
        "risk_reason",
        "summary",
        "tags",
        "next_action",
        "source_type",
        "source_metadata",
        "followup_email",
    )
    out: dict[str, Any] = {}
    for k in allow:
        if k not in record:
            continue
        out[k] = record[k]
    return out


def _groq_fallback(query: str, record: dict[str, Any]) -> str | None:
    payload = _record_for_prompt(record)
    prompt = (
        "You answer questions about ONE CRM deal. Use ONLY the JSON facts below.\n"
        'If the answer is not supported by those facts, reply exactly: Not available\n'
        "Be concise (2-4 sentences max). No bullet lists unless the user asks.\n\n"
        f"CRM_JSON:\n{json.dumps(payload, ensure_ascii=False, default=str)[:14000]}\n\n"
        f"User question: {query}\n\nAnswer:"
    )
    return groq_text_or_none(prompt, max_tokens=300, temperature=0.0)


def chat_with_deal(
    query: str,
    record: dict[str, Any],
    *,
    conversation_history: list[dict[str, str]] | None = None,
) -> str:
    q = (query or "").strip()
    if not q:
        return "Not available"

    out = chat_with_model(q, record, history=conversation_history)
    if out:
        text = out.strip()
        if len(text) > 1200:
            text = text[:1200].rsplit(" ", 1)[0] + "…"
        return text if text else "Not available"

    fb = _groq_fallback(q, record)
    if not fb:
        return "Not available"
    text = fb.strip()
    if len(text) > 1200:
        text = text[:1200].rsplit(" ", 1)[0] + "…"
    return text if text else "Not available"
