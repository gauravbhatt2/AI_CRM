"""
Evidence grounding for LLM extraction.

Any scalar field whose value cannot be located in the source transcript (as a
literal substring, a reasonable normalization, or a recognized scaled numeric
form for budget) is considered unsupported and blanked.

This is the cheapest, highest-ROI hallucination killer: it does not require a
second LLM call or any model weights.

Used by `groq_extraction.py` immediately after the facts payload is normalized.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Iterable

logger = logging.getLogger(__name__)


_WS_RE = re.compile(r"\s+")


def _normalize(text: str) -> str:
    return _WS_RE.sub(" ", text.lower()).strip()


def _literal_in(haystack_norm: str, needle: str) -> bool:
    n = _normalize(needle)
    if not n or len(n) < 2:
        return False
    return n in haystack_norm


def _budget_evidence_in(haystack: str, value: Any) -> bool:
    """True if the extracted budget value has plausible evidence in the transcript."""
    from app.utils.money_parser import parse_money_to_int

    try:
        amt = int(str(value).strip())
    except (TypeError, ValueError):
        return False
    if amt <= 0:
        return False

    for m in re.finditer(
        r"(?:\$|\u00a3|\u20ac|\u20b9|rs\.?|inr|usd|eur|gbp)?\s*"
        r"(?:(?:\d+(?:[.,]\d+)?\s*"
        r"(?:k|m|mn|million|thousand|lakhs?|crores?|cr|bn|billion)?)|"
        r"(?:(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
        r"thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|"
        r"thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|and|a|an|half)"
        r"(?:\s+(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
        r"thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|"
        r"thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|and|a|an|half))*"
        r"\s*(?:thousand|lakhs?|million|crores?|billion)))",
        haystack,
        flags=re.I,
    ):
        span = m.group(0).strip()
        cand = parse_money_to_int(span)
        if not cand:
            continue
        if cand == amt:
            return True
        if amt > 0 and 0.8 <= cand / amt <= 1.25:
            return True

    if str(amt) in re.sub(r"[,\s]", "", haystack):
        return True

    return False


def _any_token_in(haystack_norm: str, candidate: str) -> bool:
    """Relaxed check: at least half of the tokens (>=2 chars) are literally in the transcript."""
    toks = [t for t in re.findall(r"[A-Za-z0-9]+", candidate.lower()) if len(t) >= 2]
    if not toks:
        return False
    hits = sum(1 for t in toks if t in haystack_norm)
    return hits * 2 >= len(toks)


def _ground_list(haystack_norm: str, items: Iterable[Any]) -> list[str]:
    out: list[str] = []
    for v in items or []:
        s = str(v).strip()
        if not s:
            continue
        if _literal_in(haystack_norm, s) or _any_token_in(haystack_norm, s):
            out.append(s)
    return out


def ground_extracted_entities(
    entities: dict[str, Any],
    transcript: str,
    *,
    enabled: bool = True,
) -> tuple[dict[str, Any], dict[str, str]]:
    """
    Blank extracted scalar fields whose values are not supported by the transcript.

    Returns (cleaned_entities, rejected_map) where `rejected_map` names each blanked
    field and the unsupported value that was removed (useful for audit / logging).

    `enabled=False` is a pass-through; used when the operator explicitly opts out.
    """
    if not enabled or not isinstance(entities, dict) or not transcript:
        return dict(entities or {}), {}

    haystack = transcript
    haystack_norm = _normalize(haystack)
    out = dict(entities)
    rejected: dict[str, str] = {}

    scalar_fields = (
        "mentioned_company",
        "product",
        "product_version",
        "industry",
        "timeline",
        "procurement_stage",
        "use_case",
        "decision_criteria",
        "budget_owner",
        "implementation_scope",
        "pain_points",
        "next_step",
        "urgency_reason",
    )
    for f in scalar_fields:
        v = str(out.get(f) or "").strip()
        if not v or v.lower() in ("n/a", "na", "none", "unknown", "null"):
            continue
        if _literal_in(haystack_norm, v) or _any_token_in(haystack_norm, v):
            continue
        rejected[f] = v
        out[f] = ""

    b = out.get("budget")
    if b not in (None, "", "n/a"):
        if not _budget_evidence_in(haystack, b):
            rejected["budget"] = str(b)
            out["budget"] = ""

    for list_field in ("competitors", "stakeholders"):
        original = out.get(list_field) or []
        if isinstance(original, list) and original:
            kept = _ground_list(haystack_norm, original)
            if len(kept) != len(original):
                dropped = [x for x in original if x not in kept]
                if dropped:
                    rejected[list_field] = ", ".join(str(x) for x in dropped)
            out[list_field] = kept

    cf = out.get("custom_fields")
    if isinstance(cf, dict):
        cleaned_cf: dict[str, str] = {}
        for k, v in cf.items():
            sv = str(v).strip() if v is not None else ""
            if not sv:
                continue
            if _literal_in(haystack_norm, sv) or _any_token_in(haystack_norm, sv):
                cleaned_cf[k] = sv
        out["custom_fields"] = cleaned_cf

    if rejected:
        logger.info(
            "Grounded extraction removed %d unsupported field(s): %s",
            len(rejected),
            ", ".join(sorted(rejected.keys())),
        )

    return out, rejected


def ground_facts_payload(
    facts: dict[str, Any],
    transcript: str,
    *,
    enabled: bool = True,
) -> dict[str, Any]:
    """Apply grounding to the `entities` sub-object of a facts payload in place."""
    if not enabled or not isinstance(facts, dict):
        return facts
    ent = facts.get("entities")
    if not isinstance(ent, dict):
        return facts
    grounded, _ = ground_extracted_entities(ent, transcript, enabled=enabled)
    facts["entities"] = grounded
    return facts
