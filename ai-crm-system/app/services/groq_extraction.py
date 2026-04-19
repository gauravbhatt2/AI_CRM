"""
Groq LLM execution for CRM extraction: two-phase pipeline (facts → evaluation).

Prompts live in `extraction_service`. Chunking/merge in `facts_extraction`.
"""

from __future__ import annotations

import copy
import hashlib
import json
import logging
import re
import threading
from collections import OrderedDict
from typing import Any

from app.core.config import settings
from app.services.extraction_grounding import ground_extracted_entities
from app.services.groq_llm import get_groq_client
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


_extraction_cache: "OrderedDict[str, tuple[dict[str, Any], dict[str, Any], dict[str, Any]]]" = OrderedDict()
_extraction_cache_lock = threading.Lock()


def _cache_key(transcript: str) -> str:
    h = hashlib.sha256()
    h.update((settings.groq_model or "").encode("utf-8", errors="ignore"))
    h.update(b"\x00")
    h.update(
        str(bool(getattr(settings, "extraction_self_consistency", False))).encode("ascii")
    )
    h.update(b"\x00")
    h.update(
        str(bool(getattr(settings, "extraction_require_evidence", True))).encode("ascii")
    )
    h.update(b"\x00")
    h.update((transcript or "").encode("utf-8", errors="ignore"))
    return h.hexdigest()


def _cache_get(key: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]] | None:
    with _extraction_cache_lock:
        if key not in _extraction_cache:
            return None
        _extraction_cache.move_to_end(key)
        ex, ai, facts = _extraction_cache[key]
        return copy.deepcopy(ex), copy.deepcopy(ai), copy.deepcopy(facts)


def _cache_put(
    key: str,
    value: tuple[dict[str, Any], dict[str, Any], dict[str, Any]],
) -> None:
    size = int(getattr(settings, "extraction_cache_size", 0) or 0)
    if size <= 0:
        return
    ex, ai, facts = value
    with _extraction_cache_lock:
        _extraction_cache[key] = (copy.deepcopy(ex), copy.deepcopy(ai), copy.deepcopy(facts))
        _extraction_cache.move_to_end(key)
        while len(_extraction_cache) > size:
            _extraction_cache.popitem(last=False)


def clear_extraction_cache() -> None:
    """Test/ops utility."""
    with _extraction_cache_lock:
        _extraction_cache.clear()

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

_VALID_INTERACTION = frozenset({"sales", "support", "inquiry", "complaint"})
_VALID_RISK = frozenset({"low", "medium", "high"})
_VALID_INTENT = frozenset({"high", "medium", "low"})


def _is_na_token(value: Any) -> bool:
    if value is None:
        return True
    s = str(value).strip().lower()
    return s in ("", "n/a", "na", "none", "null", "unknown")


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
        return [str(x).strip() for x in value if str(x).strip() and not _is_na_token(x)]
    if isinstance(value, str) and value.strip() and not _is_na_token(value):
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
        if not ks or _is_na_token(v):
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
                "budget",
                "intent",
                "product",
                "industry",
                "timeline",
                "competitors",
                "mentioned_company",
                "procurement_stage",
                "use_case",
                "custom_fields",
                "interaction_type",
                "deal_score",
            )
        ):
            return inner
    return data


def _is_effectively_empty(norm: dict[str, Any]) -> bool:
    if not isinstance(norm, dict):
        return True
    for key in (
        "budget",
        "intent",
        "product",
        "timeline",
        "industry",
        "mentioned_company",
        "procurement_stage",
        "use_case",
        "decision_criteria",
        "pain_points",
        "next_step",
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
        return [str(x).strip() for x in value if x is not None and str(x).strip() and not _is_na_token(x)]
    if isinstance(value, str) and value.strip() and not _is_na_token(value):
        return [s.strip() for s in re.split(r"[,;]", value) if s.strip()]
    return []


def _coerce_budget(value: Any) -> str:
    """Normalize budget to a clean integer string, or empty.

    Handles plain numerics, k/m/b suffixes, spelled-out numbers
    ("seventy five thousand"), and Indian units ("5 lakh", "2 crore").
    """
    if value is None or _is_na_token(value):
        return ""
    from app.utils.money_parser import parse_money_to_str

    result = parse_money_to_str(value)
    if result:
        return result
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            return str(int(value))
        except (ValueError, OverflowError):
            return ""
    return ""


def _coerce_intent(value: Any) -> str:
    raw = str(value or "").strip().lower()
    if raw in _VALID_INTENT:
        return raw
    if _is_na_token(value):
        return "medium"
    if any(k in raw for k in ("strong", "ready", "commit", "buy", "purchase", "urgent")):
        return "high"
    if any(k in raw for k in ("evaluat", "compar", "consider", "review")):
        return "medium"
    if any(k in raw for k in ("explor", "info", "gather", "curious", "learn")):
        return "low"
    if raw:
        return "medium"
    return "medium"


def _normalize_extraction_only(data: Any) -> dict[str, Any]:
    """Normalize legacy extraction-shaped dict to DEFAULT_EXTRACTION layout."""
    out = dict(DEFAULT_EXTRACTION)
    data = _unwrap_extraction_payload(data)
    if not isinstance(data, dict):
        return out

    out["budget"] = _coerce_budget(data.get("budget"))
    out["intent"] = _coerce_intent(data.get("intent"))
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


def _scalar_from_llm(value: Any) -> str:
    if _is_na_token(value):
        return ""
    if isinstance(value, list):
        return "; ".join(str(x).strip() for x in value if str(x).strip())[:1024]
    return str(value).strip()


def facts_eval_to_extracted_and_ai(
    merged_facts: dict[str, Any],
    ev: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Combine factual JSON + evaluation JSON into legacy extraction + ai_intelligence shapes."""
    ex: dict[str, Any] = dict(DEFAULT_EXTRACTION)
    ent = merged_facts.get("entities") if isinstance(merged_facts.get("entities"), dict) else {}

    b_raw = ent.get("budget")
    if _is_na_token(b_raw):
        ex["budget"] = ""
    else:
        ex["budget"] = _coerce_budget(b_raw)

    ex["mentioned_company"] = _scalar_from_llm(ent.get("mentioned_company"))
    ex["product"] = _scalar_from_llm(ent.get("product"))
    ex["product_version"] = _scalar_from_llm(ent.get("product_version"))
    ex["competitors"] = _coerce_competitors(ent.get("competitors"))
    ex["industry"] = _scalar_from_llm(ent.get("industry"))
    ex["timeline"] = _scalar_from_llm(ent.get("timeline"))
    ex["stakeholders"] = _coerce_string_list(ent.get("stakeholders"))
    ex["procurement_stage"] = _scalar_from_llm(ent.get("procurement_stage"))[:128]
    ex["use_case"] = _scalar_from_llm(ent.get("use_case"))
    ex["decision_criteria"] = _scalar_from_llm(ent.get("decision_criteria"))
    ex["budget_owner"] = _scalar_from_llm(ent.get("budget_owner"))[:256]
    ex["implementation_scope"] = _scalar_from_llm(ent.get("implementation_scope"))[:256]
    ex["custom_fields"] = _coerce_custom_fields(ent.get("custom_fields"))

    ex["intent"] = _coerce_intent(ev.get("intent"))
    ex["pain_points"] = _scalar_from_llm(ev.get("pain_points"))
    ex["next_step"] = _scalar_from_llm(ev.get("next_step"))
    ex["urgency_reason"] = _scalar_from_llm(ev.get("urgency_reason"))

    it = str(ev.get("interaction_type") or "inquiry").strip().lower()
    if it not in _VALID_INTERACTION:
        it = "inquiry"
    try:
        ds = int(ev.get("deal_score", 0))
    except (TypeError, ValueError):
        ds = 0
    ds = max(0, min(100, ds))
    rl = str(ev.get("risk_level") or "low").strip().lower()
    if rl not in _VALID_RISK:
        rl = "low"
    next_action = _scalar_from_llm(ev.get("next_action"))[:2048]
    w = next_action.split()
    if len(w) > 12:
        next_action = " ".join(w[:12])

    tags_raw = ev.get("tags")
    tags: list[str] = []
    if isinstance(tags_raw, list):
        for t in tags_raw[:16]:
            s = str(t).strip().lower().replace(" ", "-")
            if s and not _is_na_token(s) and s not in tags:
                tags.append(s[:64])
    tags = tags[:8]

    ai = {
        "interaction_type": it,
        "deal_score": ds,
        "risk_level": rl,
        "risk_reason": _scalar_from_llm(ev.get("risk_reason"))[:2048],
        "summary": _scalar_from_llm(ev.get("summary"))[:4096],
        "next_action": next_action,
        "tags": tags,
    }
    return ex, ai


def _augment_merged_facts(merged_facts: dict[str, Any], src: str) -> dict[str, Any]:
    """Fill sparse factual output with rule-based hints (same transcript; no extra LLM)."""
    from app.services.facts_extraction import heuristics_facts_from_transcript, merge_facts_payloads

    h = heuristics_facts_from_transcript(src)
    return merge_facts_payloads([merged_facts, h])


def _finalize_two_phase(
    src: str,
    merged_facts: dict[str, Any],
    eval_block: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Heuristic merge, refiners, evidence grounding, run_ai_intelligence."""
    from app.services.ai_intelligence import run_ai_intelligence

    llm_ex, llm_ai = facts_eval_to_extracted_and_ai(merged_facts, eval_block)
    heur = heuristic_extract_entities(src)
    merged = merge_extraction_prefer_llm(llm_ex, heur)
    refine_budget_core_field(merged, src)
    if not str(merged.get("intent") or "").strip():
        merged["intent"] = "medium"
    refine_company_core_field(merged, src)
    refine_product_industry_fields(merged, src)
    refine_product_core_field(merged, src)
    refine_timeline_core_field(merged, src)
    enrich_map_version_custom_field(merged, src)

    grounding_enabled = bool(getattr(settings, "extraction_require_evidence", True))
    merged, _rejected = ground_extracted_entities(merged, src, enabled=grounding_enabled)

    ai = run_ai_intelligence(src, merged, llm_primary=llm_ai)
    return merged, ai, merged_facts


def _heuristic_fallback_pipeline(src: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """No Groq: heuristic facts + deterministic evaluation."""
    from app.services.evaluation_groq import deterministic_evaluation
    from app.services.facts_extraction import default_facts_payload, heuristics_facts_from_transcript

    facts = heuristics_facts_from_transcript(src)
    ev = deterministic_evaluation(facts)
    merged, ai, mf = _finalize_two_phase(src, facts, ev)
    return merged, ai, mf


def run_transcript_extraction_pipeline(transcript: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """
    transcript → facts (one or two Groq calls) → merge w/ heuristics → evaluation → grounding.

    Returns (extracted_entities, ai_intelligence, merged_extracted_facts). Identical
    transcripts are served from an in-process SHA256 cache (size = EXTRACTION_CACHE_SIZE).
    """
    from app.services.ai_intelligence import run_ai_intelligence
    from app.services.evaluation_groq import deterministic_evaluation, run_evaluation_groq
    from app.services.facts_extraction import (
        default_facts_payload,
        run_facts_extraction,
    )

    src = (transcript or "").strip()
    if not src:
        empty_ex = dict(DEFAULT_EXTRACTION)
        ai = run_ai_intelligence("", empty_ex, llm_primary=None)
        return empty_ex, ai, default_facts_payload()

    key = _cache_key(src)
    cached = _cache_get(key)
    if cached is not None:
        logger.info("Extraction cache hit (key=%s...)", key[:10])
        return cached

    try:
        get_groq_client()
    except RuntimeError as exc:
        logger.error("%s", exc)
        result = _heuristic_fallback_pipeline(src)
        _cache_put(key, result)
        return result

    merged_facts = run_facts_extraction(src)
    merged_facts = _augment_merged_facts(merged_facts, src)

    ev = run_evaluation_groq(merged_facts)
    if ev is None:
        ev = deterministic_evaluation(merged_facts)

    result = _finalize_two_phase(src, merged_facts, ev)
    _cache_put(key, result)
    return result


def run_unified_extraction(transcript: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Backward-compatible 2-tuple wrapper around the two-phase pipeline."""
    ex, ai, _ = run_transcript_extraction_pipeline(transcript)
    return ex, ai


def execute_groq_json_extraction(
    full_prompt: str,
    *,
    source_transcript: str | None = None,
) -> dict[str, Any]:
    """Returns extraction dict only (backward-compatible)."""
    src = (source_transcript or "").strip()
    if not src and "--- TRANSCRIPT ---" in full_prompt:
        src = full_prompt.split("--- TRANSCRIPT ---", 1)[-1].strip()
    entities, _, _ = run_transcript_extraction_pipeline(src)
    return entities


def _normalize(data: Any) -> dict[str, Any]:
    """Public alias used by tests / imports — same as extraction-only normalize."""
    return _normalize_extraction_only(data)
