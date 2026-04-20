"""
Recover missing CRM fields from structured outputs only.

This layer is intentionally transcript-blind to avoid reintroducing large prompts and
to preserve no-hallucination behavior.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import requests

from app.core.config import settings
from app.utils.groq_retry import groq_chat_with_retry

logger = logging.getLogger(__name__)

RECOVERABLE_FIELDS: tuple[str, ...] = (
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
)


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip().lower() in {"", "n/a", "na", "none", "null", "unknown"}
    if isinstance(value, (list, dict)):
        return len(value) == 0
    return False


def _parse_json_object(raw: str) -> dict[str, Any] | None:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE).strip()
        text = re.sub(r"\s*```\s*$", "", text).strip()
    try:
        parsed = json.loads(text)
    except Exception:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            return None
        try:
            parsed = json.loads(text[start : end + 1])
        except Exception:
            return None
    return parsed if isinstance(parsed, dict) else None


def _recovery_prompt(
    *,
    missing_fields: list[str],
    extracted: dict[str, Any],
    ai: dict[str, Any],
    merged_facts: dict[str, Any],
) -> str:
    context = {
        "summary": str(ai.get("summary") or "").strip(),
        "intent": str(extracted.get("intent") or "").strip(),
        "pain_points": str(extracted.get("pain_points") or "").strip(),
        "next_action": str(ai.get("next_action") or "").strip(),
        "extracted_fields": {k: extracted.get(k) for k in RECOVERABLE_FIELDS if k in extracted},
        "merged_facts_entities": (merged_facts.get("entities") or {}) if isinstance(merged_facts, dict) else {},
    }
    compact = json.dumps(context, ensure_ascii=False, separators=(",", ":"))[:30_000]
    return (
        "You complete missing CRM fields.\n"
        "Use ONLY the structured context below.\n"
        "Do NOT hallucinate. If unsure, return null.\n"
        "Do not include fields outside the request.\n\n"
        f"Fields to fill: {json.dumps(missing_fields)}\n\n"
        "Return one JSON object mapping each requested field to value or null.\n"
        "Rules:\n"
        '- budget must be integer-like text (example: "50000") or null.\n'
        '- competitors/stakeholders must be arrays when present.\n'
        "- Keep values concise and grounded.\n\n"
        f"CONTEXT_JSON:\n{compact}"
    )


def _normalize_field(field: str, value: Any) -> Any:
    if value is None:
        return None
    if field == "budget":
        s = str(value).strip()
        return s if s.isdigit() else None
    if field in ("competitors", "stakeholders"):
        if isinstance(value, list):
            out = [str(x).strip() for x in value if str(x).strip()]
            return out[:32]
        if isinstance(value, str):
            out = [x.strip() for x in re.split(r"[,;]", value) if x.strip()]
            return out[:32] if out else None
        return None
    s = str(value).strip()
    if not s or s.lower() in {"n/a", "na", "none", "null", "unknown"}:
        return None
    return s[:2048]


def _recover_with_openrouter(prompt: str) -> dict[str, Any] | None:
    key = (getattr(settings, "openrouter_api_key", None) or "").strip()
    if not key:
        return None
    base = (getattr(settings, "openrouter_base_url", None) or "https://openrouter.ai/api/v1").strip().rstrip("/")
    model = (getattr(settings, "openrouter_model", None) or "google/gemma-3-12b-it:free").strip()
    timeout = float(getattr(settings, "openrouter_timeout_sec", 25.0) or 25.0)
    url = f"{base}/chat/completions"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "HTTP-Referer": getattr(settings, "openrouter_referer", "https://localhost") or "https://localhost",
        "X-Title": getattr(settings, "app_name", "AI CRM") or "AI CRM",
    }
    body: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0,
        "max_tokens": 2048,
        "response_format": {"type": "json_object"},
    }
    try:
        r = requests.post(url, headers=headers, json=body, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        raw = ((data.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
    except Exception as exc:
        logger.warning("OpenRouter missing-field recovery failed: %s", exc)
        return None
    return _parse_json_object(str(raw))


def _recover_with_groq(prompt: str) -> dict[str, Any] | None:
    if not (settings.groq_model or "").strip():
        return None
    try:
        raw = groq_chat_with_retry(
            prompt,
            json_mode=True,
            max_attempts=2,
            temperature=0.0,
            top_p=1.0,
            max_tokens=2048,
        )
    except Exception as exc:
        logger.warning("Groq missing-field recovery failed: %s", exc)
        return None
    return _parse_json_object(raw)


def recover_missing_fields(
    extracted: dict[str, Any],
    ai: dict[str, Any],
    merged_facts: dict[str, Any],
) -> dict[str, Any]:
    """
    Fill only empty extraction fields from structured context.
    Returns partial patch dict (only safe recovered keys).
    """
    missing = [f for f in RECOVERABLE_FIELDS if _is_missing(extracted.get(f))]
    if not missing:
        return {}

    prompt = _recovery_prompt(
        missing_fields=missing,
        extracted=extracted,
        ai=ai,
        merged_facts=merged_facts,
    )
    parsed = _recover_with_openrouter(prompt) or _recover_with_groq(prompt)
    if not parsed:
        return {}

    patch: dict[str, Any] = {}
    for field in missing:
        if field not in parsed:
            continue
        norm = _normalize_field(field, parsed.get(field))
        if norm is None:
            continue
        if _is_missing(extracted.get(field)):
            patch[field] = norm
    return patch

