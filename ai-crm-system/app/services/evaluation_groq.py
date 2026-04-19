"""
Evaluation layer: intent, pain points, deal signals — inferred ONLY from merged factual JSON.

No raw transcript in the primary LLM call (hallucination control). Deterministic fallback uses
facts-derived text only.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.core.config import settings
from app.services.extraction_service import build_evaluation_prompt
from app.services.groq_llm import get_groq_client
from app.utils.groq_retry import groq_chat_with_retry

logger = logging.getLogger(__name__)

EVAL_REQUIRED_KEYS: frozenset[str] = frozenset(
    {
        "intent",
        "pain_points",
        "next_step",
        "next_action",
        "risk_level",
        "risk_reason",
        "deal_score",
        "interaction_type",
        "summary",
        "tags",
        "urgency_reason",
    }
)

_VALID_INTERACTION = frozenset({"sales", "support", "inquiry", "complaint"})
_VALID_RISK = frozenset({"low", "medium", "high"})
_VALID_INTENT = frozenset({"high", "medium", "low"})


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


def validate_evaluation_payload(data: Any) -> bool:
    if not isinstance(data, dict):
        return False
    if not EVAL_REQUIRED_KEYS <= data.keys():
        return False
    if not isinstance(data.get("tags"), list):
        return False
    try:
        ds = int(data.get("deal_score", 0))
        if ds < 0 or ds > 100:
            return False
    except (TypeError, ValueError):
        return False
    return True


def default_evaluation_payload() -> dict[str, Any]:
    return {
        "intent": "medium",
        "pain_points": "n/a",
        "next_step": "n/a",
        "next_action": "n/a",
        "risk_level": "low",
        "risk_reason": "n/a",
        "deal_score": 0,
        "interaction_type": "inquiry",
        "summary": "n/a",
        "tags": [],
        "urgency_reason": "n/a",
    }


def _normalize_evaluation(data: dict[str, Any]) -> dict[str, Any]:
    out = default_evaluation_payload()
    out["intent"] = str(data.get("intent") or "medium").strip().lower()
    if out["intent"] not in _VALID_INTENT:
        out["intent"] = "medium"
    out["pain_points"] = str(data.get("pain_points") or "").strip()[:2048]
    out["next_step"] = str(data.get("next_step") or "").strip()[:2048]
    na = str(data.get("next_action") or "").strip()
    words = na.split()
    if len(words) > 12:
        na = " ".join(words[:12])
    out["next_action"] = na[:2048]
    rl = str(data.get("risk_level") or "low").strip().lower()
    out["risk_level"] = rl if rl in _VALID_RISK else "low"
    out["risk_reason"] = str(data.get("risk_reason") or "").strip()[:2048]
    try:
        out["deal_score"] = max(0, min(100, int(data.get("deal_score", 0))))
    except (TypeError, ValueError):
        out["deal_score"] = 0
    it = str(data.get("interaction_type") or "inquiry").strip().lower()
    out["interaction_type"] = it if it in _VALID_INTERACTION else "inquiry"
    out["summary"] = str(data.get("summary") or "").strip()[:4096]
    out["urgency_reason"] = str(data.get("urgency_reason") or "").strip()[:2048]
    tags_raw = data.get("tags")
    tags: list[str] = []
    if isinstance(tags_raw, list):
        for t in tags_raw[:16]:
            s = str(t).strip().lower().replace(" ", "-")
            if s and s not in tags:
                tags.append(s[:64])
    out["tags"] = tags[:8]
    return out


def facts_to_synthetic_text(facts: dict[str, Any]) -> str:
    """Compact text for deterministic helpers — derived only from facts JSON."""
    blob = json.dumps(facts, ensure_ascii=False, indent=0)
    return blob[:12000]


def run_evaluation_groq(merged_facts: dict[str, Any]) -> dict[str, Any] | None:
    """Single Groq call: evaluate using merged facts JSON only."""
    if not (settings.groq_model or "").strip():
        return None
    try:
        get_groq_client()
    except RuntimeError:
        return None

    facts_json = json.dumps(merged_facts, ensure_ascii=False)[:28000]
    prompt = build_evaluation_prompt(facts_json)
    try:
        raw = groq_chat_with_retry(
            prompt,
            json_mode=True,
            max_attempts=3,
            temperature=0.0,
            top_p=1.0,
            max_tokens=4096,
        )
    except Exception:
        logger.exception("Groq evaluation request failed")
        return None
    if not raw:
        return None
    parsed = _parse_json_loose(raw)
    if not isinstance(parsed, dict):
        return None
    if not validate_evaluation_payload(parsed):
        logger.warning("Evaluation payload invalid")
        return None
    return _normalize_evaluation(parsed)


def deterministic_evaluation(merged_facts: dict[str, Any]) -> dict[str, Any]:
    """Heuristic scoring from facts-only synthetic text (no extra LLM)."""
    from app.services.ai_intelligence import (
        auto_tag,
        classify_interaction,
        detect_risk,
        generate_next_action,
        generate_summary,
        score_deal,
    )

    syn = facts_to_synthetic_text(merged_facts)
    ent = merged_facts.get("entities") if isinstance(merged_facts.get("entities"), dict) else {}
    record: dict[str, Any] = {
        "budget": str(ent.get("budget") or ""),
        "intent": "medium",
        "competitors": ent.get("competitors") or [],
        "product": str(ent.get("product") or ""),
        "timeline": str(ent.get("timeline") or ""),
        "mentioned_company": str(ent.get("mentioned_company") or ""),
        "procurement_stage": str(ent.get("procurement_stage") or ""),
        "use_case": str(ent.get("use_case") or ""),
        "decision_criteria": str(ent.get("decision_criteria") or ""),
        "pain_points": "",
        "next_step": "",
    }
    record["intent"] = "medium"
    if str(ent.get("budget") or "").isdigit():
        record["intent"] = "high"
    risk = detect_risk(syn)
    summary = generate_summary(syn, record)
    next_action = generate_next_action(syn)
    return _normalize_evaluation(
        {
            "intent": record["intent"],
            "pain_points": "n/a",
            "next_step": "n/a",
            "next_action": next_action,
            "risk_level": risk["risk_level"],
            "risk_reason": risk["reason"],
            "deal_score": score_deal(record),
            "interaction_type": classify_interaction(syn),
            "summary": summary,
            "tags": auto_tag(syn),
            "urgency_reason": "n/a",
        }
    )
