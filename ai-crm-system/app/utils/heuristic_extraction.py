"""
Rule-based CRM field hints when the Groq API is unavailable (quota, network).

Intended as a fallback only — lower quality than LLM extraction.
"""

from __future__ import annotations

import re
from typing import Any


def heuristic_extract_entities(transcript: str) -> dict[str, Any]:
    """Return the same shape as the LLM extraction JSON."""
    t = (transcript or "").strip()
    out: dict[str, Any] = {
        "budget": "",
        "intent": "",
        "competitors": [],
        "product": "",
        "timeline": "",
        "industry": "",
        "custom_fields": {},
    }
    if not t:
        return out

    bm = re.search(
        r"\bbudget\s+(?:is|of|around|about)?\s*[:\s]*([₹$€]?\s*[\d,.]+(?:\s*[kKmM])?)",
        t,
        re.I,
    )
    if bm:
        out["budget"] = re.sub(r"\s+", " ", bm.group(1).strip())
    else:
        bm2 = re.search(
            r"(?:₹|\$|€|inr|usd)\s*[\d,.]+|[\d]{1,3}(?:,\d{3})+(?:\.\d+)?|\b\d+\s*[kKmM]\b",
            t,
            re.I,
        )
        if bm2:
            out["budget"] = bm2.group(0).strip()

    fm = re.search(
        r"\bfrom\s+([A-Z][a-zA-Z0-9&.'-]+(?:\s+[A-Z][a-zA-Z0-9&.'-]+)*)",
        t,
    )
    if fm:
        company = fm.group(1).strip()
        if len(company) >= 2:
            out["custom_fields"]["mentioned_company"] = company[:256]

    pm = re.search(
        r"\b(?:call|spoke|talked|meeting)\s+with\s+([A-Z][a-z]+)\s+from\b",
        t,
        re.I,
    )
    if pm:
        out["custom_fields"]["contact_person"] = pm.group(1)

    if re.search(r"\bgo\s*live\b", t, re.I):
        out["timeline"] = "go live (mentioned)"
    elif re.search(
        r"\b(?:Q[1-4]\s*\d{4}|next\s+(?:week|month|quarter)|within\s+\d+\s*(?:days|weeks|months))\b",
        t,
        re.I,
    ):
        out["timeline"] = "timeframe mentioned in conversation"

    if re.search(r"\b(?:competitor|vs\.?|versus)\s+([A-Z][a-zA-Z]+)", t):
        cm = re.findall(r"\b(?:vs\.?|versus)\s+([A-Z][a-zA-Z0-9]+)", t)
        out["competitors"] = list({c for c in cm if c})[:10]

    low = bool(re.search(r"\b(?:maybe|not sure|just looking|explor(?:e|ing))\b", t, re.I))
    high = bool(
        re.search(
            r"\b(?:purchase order|signed|ready to buy|send (?:the )?contract)\b",
            t,
            re.I,
        )
    )
    if high:
        out["intent"] = "high"
    elif low:
        out["intent"] = "low"
    elif re.search(r"\b(?:budget|pricing|proposal|demo|pilot)\b", t, re.I):
        out["intent"] = "medium"

    return out


def merge_extraction_prefer_llm(llm: dict[str, Any], heur: dict[str, Any]) -> dict[str, Any]:
    """Fill empty LLM fields from heuristics; LLM non-empty values win."""
    out = dict(llm)
    if not isinstance(heur, dict):
        return out

    for key in ("budget", "intent", "product", "timeline", "industry"):
        lv = str(out.get(key) or "").strip()
        hv = str(heur.get(key) or "").strip()
        if not lv and hv:
            out[key] = hv

    if not out.get("competitors") and heur.get("competitors"):
        out["competitors"] = list(heur["competitors"])

    llm_cf = out.get("custom_fields") if isinstance(out.get("custom_fields"), dict) else {}
    h_cf = heur.get("custom_fields") if isinstance(heur.get("custom_fields"), dict) else {}
    merged_cf = dict(h_cf)
    merged_cf.update(llm_cf)
    out["custom_fields"] = merged_cf
    return out
