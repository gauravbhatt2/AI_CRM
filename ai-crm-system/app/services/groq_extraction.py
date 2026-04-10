"""
Groq LLM execution for CRM extraction: JSON responses and defensive parsing.

Prompt construction lives in `extraction_service` (see `build_extraction_prompt`).
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from openai import RateLimitError

from app.core.config import settings
from app.services.groq_llm import get_groq_client
from app.utils.groq_retry import groq_chat_with_retry
from app.utils.heuristic_extraction import heuristic_extract_entities, merge_extraction_prefer_llm

logger = logging.getLogger(__name__)

DEFAULT_EXTRACTION: dict[str, Any] = {
    "budget": "",
    "intent": "",
    "competitors": [],
    "product": "",
    "timeline": "",
    "industry": "",
    "custom_fields": {},
}


def _strip_markdown_fences(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```\s*$", "", text)
    return text.strip()


def _parse_json_loose(raw: str) -> Any | None:
    cleaned = _strip_markdown_fences(raw)
    try:
        return json.loads(cleaned)
    except (json.JSONDecodeError, TypeError, ValueError):
        pass
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(cleaned[start : end + 1])
        except (json.JSONDecodeError, TypeError, ValueError):
            return None
    return None


def _coerce_competitors(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    if isinstance(value, str) and value.strip():
        return [c.strip() for c in re.split(r"[,;]", value) if c.strip()]
    return []


def _coerce_custom_fields(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    out: dict[str, str] = {}
    for i, (k, v) in enumerate(value.items()):
        if i >= 20:
            break
        ks = str(k).strip()
        if not ks:
            continue
        out[ks[:128]] = str(v).strip()[:2048] if v is not None else ""
    return out


def _unwrap_extraction_payload(data: Any) -> Any:
    if isinstance(data, list) and len(data) == 1:
        data = data[0]
    if not isinstance(data, dict):
        return data
    for key in (
        "extraction",
        "extracted_entities",
        "extracted",
        "result",
        "crm",
        "fields",
        "data",
        "output",
        "response",
    ):
        inner = data.get(key)
        if isinstance(inner, dict) and any(
            k in inner
            for k in ("budget", "intent", "product", "industry", "timeline", "competitors", "custom_fields")
        ):
            return inner
    return data


def _is_effectively_empty(norm: dict[str, Any]) -> bool:
    if not isinstance(norm, dict):
        return True
    if str(norm.get("budget") or "").strip():
        return False
    if str(norm.get("intent") or "").strip():
        return False
    if str(norm.get("product") or "").strip():
        return False
    if str(norm.get("timeline") or "").strip():
        return False
    if str(norm.get("industry") or "").strip():
        return False
    if norm.get("competitors"):
        return False
    cf = norm.get("custom_fields")
    if isinstance(cf, dict) and cf:
        return False
    return True


def _normalize(data: Any) -> dict[str, Any]:
    out = dict(DEFAULT_EXTRACTION)
    data = _unwrap_extraction_payload(data)
    if not isinstance(data, dict):
        return out
    b = data.get("budget")
    if isinstance(b, (int, float)):
        out["budget"] = str(b)
    else:
        out["budget"] = str(b or "").strip()
    out["intent"] = str(data.get("intent") or "").strip()
    out["product"] = str(data.get("product") or "").strip()
    out["timeline"] = str(data.get("timeline") or "").strip()
    out["industry"] = str(data.get("industry") or "").strip()
    out["competitors"] = _coerce_competitors(data.get("competitors"))
    out["custom_fields"] = _coerce_custom_fields(data.get("custom_fields"))
    return out


def _run_groq_extraction_attempt(
    full_prompt: str,
    *,
    json_mode: bool,
) -> tuple[dict[str, Any], bool, bool]:
    """
    Returns (normalized dict, success, rate_limit_skip_followup).

    If rate_limit_skip_followup is True, skip a second LLM extraction attempt (429 after retries).
    """
    if not (settings.groq_model or "").strip():
        logger.error("GROQ_MODEL is not set")
        return dict(DEFAULT_EXTRACTION), False, False

    try:
        raw = groq_chat_with_retry(full_prompt, json_mode=json_mode, max_attempts=3)
    except RateLimitError as e:
        logger.warning(
            "Groq extraction rate limited after retries; using heuristic fallback if needed: %s",
            e,
        )
        return dict(DEFAULT_EXTRACTION), False, True
    except Exception:
        logger.exception("Groq extraction request failed (json_mode=%s)", json_mode)
        return dict(DEFAULT_EXTRACTION), False, False

    if not raw:
        logger.warning("Groq returned empty extraction text (json_mode=%s)", json_mode)
        return dict(DEFAULT_EXTRACTION), False, False

    parsed = _parse_json_loose(raw)
    if parsed is None:
        logger.warning(
            "Failed to parse Groq extraction as JSON (json_mode=%s); raw prefix: %s",
            json_mode,
            raw[:1200] if raw else "",
        )
        return dict(DEFAULT_EXTRACTION), False, False

    return _normalize(parsed), True, False


def _transcript_from_prompt(full_prompt: str) -> str:
    if "Conversation:\n" in full_prompt:
        return full_prompt.split("Conversation:\n", 1)[-1].strip()
    return ""


def execute_groq_json_extraction(
    full_prompt: str,
    *,
    source_transcript: str | None = None,
) -> dict[str, Any]:
    """
    Send `full_prompt` to Groq and return normalized extraction dict.

    On missing configuration, API errors, or invalid JSON, merges heuristic fallback where useful.
    """
    src_early = (source_transcript or _transcript_from_prompt(full_prompt) or "").strip()

    if not full_prompt or not full_prompt.strip():
        return merge_extraction_prefer_llm(dict(DEFAULT_EXTRACTION), heuristic_extract_entities(src_early))

    try:
        get_groq_client()
    except RuntimeError as exc:
        logger.error("%s", exc)
        return merge_extraction_prefer_llm(dict(DEFAULT_EXTRACTION), heuristic_extract_entities(src_early))

    first, ok, rl_skip = _run_groq_extraction_attempt(full_prompt, json_mode=True)

    if rl_skip:
        llm_out = first
    elif ok and not _is_effectively_empty(first):
        llm_out = first
    else:
        llm_out = first
        if ok and _is_effectively_empty(first):
            logger.warning(
                "Groq JSON-mode extraction returned only empty fields; retrying without JSON schema",
            )
        fallback_prompt = (
            full_prompt
            + "\n\nReply with ONLY a single JSON object matching the format above. "
            "No markdown fences, no commentary."
        )
        second, ok2, rl2 = _run_groq_extraction_attempt(
            fallback_prompt,
            json_mode=False,
        )
        if not rl2:
            if ok2 and not _is_effectively_empty(second):
                llm_out = second
            elif ok and not _is_effectively_empty(first):
                llm_out = first
            else:
                llm_out = second if ok2 else first

    heur = heuristic_extract_entities(src_early)
    merged = merge_extraction_prefer_llm(llm_out, heur)
    if _is_effectively_empty(llm_out) and not _is_effectively_empty(merged):
        logger.info(
            "Filled CRM fields from heuristic fallback (Groq unavailable, empty, or rate limited)",
        )
    return merged
