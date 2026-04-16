"""
Rule-based CRM field hints when the Groq API is unavailable (quota, network).

Intended as a fallback only — lower quality than LLM extraction.
"""

from __future__ import annotations

import re
from typing import Any

from app.utils.extraction_refine import (
    infer_budget_hint,
    infer_company_hint,
    infer_industry_hint,
    infer_product_hint,
    infer_timeline_hint,
)


def heuristic_extract_entities(transcript: str) -> dict[str, Any]:
    """Return the same shape as the LLM extraction JSON."""
    t = (transcript or "").strip()
    out: dict[str, Any] = {
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
    if not t:
        return out

    b_hint = infer_budget_hint(t)
    if b_hint:
        out["budget"] = b_hint

    company = infer_company_hint(t)
    if company:
        out["mentioned_company"] = company[:256]
        out["custom_fields"]["mentioned_company"] = company[:256]

    pm = re.search(
        r"\b(?:call|spoke|talked|meeting)\s+with\s+([A-Z][a-z]+)\s+from\b",
        t,
        re.I,
    )
    if pm:
        out["custom_fields"]["contact_person"] = pm.group(1)

    th = infer_timeline_hint(t)
    if th:
        out["timeline"] = th

    p_hint = infer_product_hint(t)
    if p_hint:
        out["product"] = p_hint[:512]

    i_hint = infer_industry_hint(t)
    if i_hint:
        out["industry"] = i_hint[:256]

    pain_candidates: list[str] = []
    m_issue = re.search(r"\b(?:biggest issue|biggest challenge|main challenge)\s+is\s+([^.]+)", t, re.I)
    if m_issue:
        pain_candidates.append(m_issue.group(1).strip(" .,:;"))
    if re.search(r"\bmanual(?:ly)?\b", t, re.I):
        pain_candidates.append("Manual CRM/call logging effort")
    if re.search(r"\black of (?:clear )?view|visibility\b", t, re.I):
        pain_candidates.append("Limited pipeline visibility")
    if re.search(r"\breport(?:ing)?\b", t, re.I) and re.search(r"\b(?:time|slow|reliable|accuracy|accurate)\b", t, re.I):
        pain_candidates.append("Reporting is slow and data reliability is poor")
    if re.search(r"\bdifficult to manage|hard to manage|inefficient\b", t, re.I):
        pain_candidates.append("Current workflow is difficult to manage efficiently")
    if pain_candidates:
        dedup = list(dict.fromkeys(pain_candidates))
        out["pain_points"] = "; ".join(dedup)[:1024]

    competitors: list[str] = []
    if re.search(r"\b(?:competitor|vs\.?|versus)\s+([A-Z][a-zA-Z]+)", t):
        cm = re.findall(r"\b(?:vs\.?|versus)\s+([A-Z][a-zA-Z0-9]+)", t)
        competitors.extend([c for c in cm if c])
    looked_into = re.findall(r"\blooked into\s+([A-Z][a-zA-Z0-9]+)", t, re.I)
    competitors.extend([c for c in looked_into if c])
    if competitors:
        out["competitors"] = list(dict.fromkeys(competitors))[:10]

    low = bool(
        re.search(
            r"\b(?:not sure|just looking|explor(?:e|ing)|can't afford|cannot afford|too expensive|no budget)\b",
            t,
            re.I,
        )
    )
    high = bool(
        re.search(
            r"\b(?:purchase order|signed|ready to buy|send (?:the )?contract|let'?s go ahead|use a visa|place this order|set this order up)\b",
            t,
            re.I,
        )
    )
    medium = bool(
        re.search(
            r"\b(?:timeline|next quarter|next two months|head of sales|decision|stakeholder|demo|hubspot|integration|proposal|budget)\b",
            t,
            re.I,
        )
    )
    if high:
        out["intent"] = "high"
    elif low:
        out["intent"] = "low"
    elif medium or re.search(r"\b(?:budget|pricing|proposal|demo|pilot)\b", t, re.I):
        out["intent"] = "medium"

    return out


def merge_extraction_prefer_llm(llm: dict[str, Any], heur: dict[str, Any]) -> dict[str, Any]:
    """Fill empty LLM fields from heuristics; LLM non-empty values win."""
    out = dict(llm)
    if not isinstance(heur, dict):
        return out

    for key in (
        "budget", "intent", "product", "product_version", "timeline",
        "industry", "pain_points", "next_step", "urgency_reason",
        "mentioned_company", "procurement_stage", "use_case",
        "decision_criteria", "budget_owner", "implementation_scope",
    ):
        lv = str(out.get(key) or "").strip()
        hv = str(heur.get(key) or "").strip()
        if not lv and hv:
            out[key] = hv

    if not out.get("competitors") and heur.get("competitors"):
        out["competitors"] = list(heur["competitors"])
    if not out.get("stakeholders") and heur.get("stakeholders"):
        out["stakeholders"] = list(heur["stakeholders"])

    llm_cf = out.get("custom_fields") if isinstance(out.get("custom_fields"), dict) else {}
    h_cf = heur.get("custom_fields") if isinstance(heur.get("custom_fields"), dict) else {}
    merged_cf = dict(h_cf)
    merged_cf.update(llm_cf)
    out["custom_fields"] = merged_cf
    return out
