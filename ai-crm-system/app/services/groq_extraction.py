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
from app.utils.extraction_refine import (
    refine_budget_core_field,
    refine_company_core_field,
    refine_product_industry_fields,
    enrich_map_version_custom_field,
    refine_product_core_field,
    refine_timeline_core_field,
)
from app.utils.heuristic_extraction import heuristic_extract_entities, merge_extraction_prefer_llm

logger = logging.getLogger(__name__)

DEFAULT_EXTRACTION: dict[str, Any] = {
    "budget": "",
    "intent": "",
    "competitors": [],
    "product": "",
    "product_version": "",
    "timeline": "",
    "industry": "",
    "pain_points": "",
    "next_step": "",
    "urgency_reason": "",
    "stakeholders": [],
    "mentioned_company": "",
    "procurement_stage": "",
    "use_case": "",
    "decision_criteria": "",
    "budget_owner": "",
    "implementation_scope": "",
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
            for k in (
                "budget", "intent", "product", "industry", "timeline",
                "competitors", "mentioned_company", "procurement_stage",
                "use_case", "custom_fields",
            )
        ):
            return inner
    return data


def _is_effectively_empty(norm: dict[str, Any]) -> bool:
    if not isinstance(norm, dict):
        return True
    for key in (
        "budget", "intent", "product", "timeline", "industry",
        "mentioned_company", "procurement_stage", "use_case",
        "decision_criteria", "pain_points", "next_step",
    ):
        if str(norm.get(key) or "").strip():
            return False
    if norm.get("competitors"):
        return False
    if norm.get("stakeholders"):
        return False
    cf = norm.get("custom_fields")
    if isinstance(cf, dict) and cf:
        return False
    return True


def _coerce_string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(x).strip() for x in value if x is not None and str(x).strip()]
    if isinstance(value, str) and value.strip():
        return [s.strip() for s in re.split(r"[,;]", value) if s.strip()]
    return []


def _coerce_budget(value: Any) -> str:
    """Normalize budget to a clean integer string, or empty."""
    if value is None:
        return ""
    if isinstance(value, (int, float)):
        return str(int(value))
    raw = str(value).strip()
    if not raw:
        return ""
    cleaned = re.sub(r"[,$£€\s]", "", raw)
    m = re.match(r"^(\d+(?:\.\d+)?)\s*([kKmM])?$", cleaned)
    if m:
        num = float(m.group(1))
        suffix = (m.group(2) or "").lower()
        if suffix == "k":
            num *= 1_000
        elif suffix == "m":
            num *= 1_000_000
        return str(int(num))
    digits = re.sub(r"[^\d.]", "", raw)
    if digits:
        try:
            return str(int(float(digits)))
        except (ValueError, OverflowError):
            pass
    return raw


def _coerce_intent(value: Any) -> str:
    """Normalize intent to exactly 'high', 'medium', or 'low'."""
    raw = str(value or "").strip().lower()
    if raw in ("high", "medium", "low"):
        return raw
    if any(k in raw for k in ("strong", "ready", "commit", "buy", "purchase", "urgent")):
        return "high"
    if any(k in raw for k in ("evaluat", "compar", "consider", "review")):
        return "medium"
    if any(k in raw for k in ("explor", "info", "gather", "curious", "learn")):
        return "low"
    if raw:
        return "medium"
    return ""


def _normalize(data: Any) -> dict[str, Any]:
    out = dict(DEFAULT_EXTRACTION)
    data = _unwrap_extraction_payload(data)
    if not isinstance(data, dict):
        return out

    out["budget"] = _coerce_budget(data.get("budget"))
    out["intent"] = _coerce_intent(data.get("intent")) or "medium"
    out["product"] = str(data.get("product") or "").strip()
    out["product_version"] = str(data.get("product_version") or "").strip()
    out["timeline"] = str(data.get("timeline") or "").strip()
    out["industry"] = str(data.get("industry") or "").strip()

    pp = data.get("pain_points")
    if isinstance(pp, list):
        out["pain_points"] = "; ".join(str(x).strip() for x in pp if x is not None and str(x).strip())
    else:
        out["pain_points"] = str(pp or "").strip()

    out["next_step"] = str(data.get("next_step") or "").strip()
    out["urgency_reason"] = str(data.get("urgency_reason") or "").strip()
    out["stakeholders"] = _coerce_string_list(data.get("stakeholders"))
    out["competitors"] = _coerce_competitors(data.get("competitors"))

    out["mentioned_company"] = str(data.get("mentioned_company") or "").strip()
    out["procurement_stage"] = str(data.get("procurement_stage") or "").strip()
    out["use_case"] = str(data.get("use_case") or "").strip()
    out["decision_criteria"] = str(data.get("decision_criteria") or "").strip()
    out["budget_owner"] = str(data.get("budget_owner") or "").strip()
    out["implementation_scope"] = str(data.get("implementation_scope") or "").strip()

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
    refine_budget_core_field(merged, src_early)
    if not str(merged.get("intent") or "").strip():
        merged["intent"] = "medium"
    refine_company_core_field(merged, src_early)
    refine_product_industry_fields(merged, src_early)
    refine_product_core_field(merged, src_early)
    refine_timeline_core_field(merged, src_early)
    enrich_map_version_custom_field(merged, src_early)
    if _is_effectively_empty(llm_out) and not _is_effectively_empty(merged):
        logger.info(
            "Filled CRM fields from heuristic fallback (Groq unavailable, empty, or rate limited)",
        )
    return merged
