"""
Deal chat via OpenRouter (e.g. Gemma). Uses structured CRM fields only — no raw transcript.

Fast path: short timeout, optional last-N message memory for continuity.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import requests

from app.core.config import settings

logger = logging.getLogger(__name__)

# Fields allowed in chat context (excludes full transcript / content)
_CRM_CHAT_FIELDS = frozenset(
    {
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
        "id",
        "record_id",
        "source_type",
    }
)


def _crm_payload_for_chat(record: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k in _CRM_CHAT_FIELDS:
        if k not in record:
            continue
        v = record[k]
        if isinstance(v, str) and len(v) > 8000:
            out[k] = v[:4000] + "…"
        else:
            out[k] = v
    return out


def chat_with_model(
    query: str,
    record: dict[str, Any],
    *,
    history: list[dict[str, str]] | None = None,
) -> str | None:
    """
    OpenRouter chat completion. Returns None if misconfigured or request fails.

    `history`: optional prior turns [{"role":"user"|"assistant","content":"..."}] (max ~3 pairs used).
    """
    key = (getattr(settings, "openrouter_api_key", None) or "").strip()
    if not key:
        return None

    base = (getattr(settings, "openrouter_base_url", None) or "https://openrouter.ai/api/v1").strip().rstrip("/")
    model = (getattr(settings, "openrouter_model", None) or "google/gemma-3-12b-it:free").strip()
    timeout = float(getattr(settings, "openrouter_timeout_sec", 25.0) or 25.0)

    payload_json = json.dumps(_crm_payload_for_chat(record), ensure_ascii=False, default=str)[:14000]

    system = (
        "You are a helpful CRM assistant. Answer using ONLY the CRM_DEAL_JSON facts below. "
        "Do not invent data. If the facts do not support an answer, say you don't have that information. "
        "Be concise and natural (2–5 sentences unless the user asks for detail)."
    )

    messages: list[dict[str, str]] = [{"role": "system", "content": f"{system}\n\nCRM_DEAL_JSON:\n{payload_json}"}]

    if history:
        for h in history[-6:]:
            role = str(h.get("role") or "").strip().lower()
            content = str(h.get("content") or "").strip()
            if role not in ("user", "assistant") or not content:
                continue
            messages.append({"role": role, "content": content[:4000]})

    messages.append({"role": "user", "content": (query or "").strip()[:4000]})

    url = f"{base}/chat/completions"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "HTTP-Referer": getattr(settings, "openrouter_referer", "https://localhost") or "https://localhost",
        "X-Title": getattr(settings, "app_name", "AI CRM") or "AI CRM",
    }
    body: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 400,
    }

    try:
        r = requests.post(url, headers=headers, json=body, timeout=timeout)
        r.raise_for_status()
        data = r.json()
    except Exception as exc:
        logger.warning("OpenRouter chat failed: %s", exc)
        return None

    try:
        choice = (data.get("choices") or [{}])[0]
        msg = choice.get("message") or {}
        text = (msg.get("content") or "").strip()
    except (TypeError, AttributeError, IndexError):
        return None

    if not text:
        return None
    if len(text) > 2000:
        text = text[:2000].rsplit(" ", 1)[0] + "…"
    return text
