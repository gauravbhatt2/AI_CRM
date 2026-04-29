"""
Factual extraction only (no intent, pain, or deal scoring).

Single-pass transcript → facts JSON. Used by the two-phase pipeline.
"""

from __future__ import annotations

import json
import logging
import re
from collections import Counter
from typing import Any

from app.core.config import settings
from app.services.extraction_service import (
    build_facts_extraction_prompt,
)
from app.services.groq_llm import get_groq_client
from app.utils.groq_retry import groq_chat_with_retry

logger = logging.getLogger(__name__)

FACTS_REQUIRED_TOP: frozenset[str] = frozenset({"statements", "entities", "participants", "timestamps"})
TOKENS_CHAR_RATIO = 4
MAX_FACTS_INPUT_TOKENS = 10_000
FACTS_CHUNK_TOKENS = 800
FACTS_CHUNK_OVERLAP_TOKENS = 80

_ENT_KEYS_EXPECTED = frozenset(
    {
        "mentioned_company",
        "product",
        "product_version",
        "budget",
        "competitors",
        "industry",
        "timeline",
        "stakeholders",
        "procurement_stage",
        "use_case",
        "decision_criteria",
        "budget_owner",
        "implementation_scope",
        "custom_fields",
    }
)


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


def validate_facts_payload(data: Any) -> bool:
    if not isinstance(data, dict):
        return False
    if not FACTS_REQUIRED_TOP <= data.keys():
        return False
    if not isinstance(data.get("statements"), list):
        return False
    if not isinstance(data.get("entities"), dict):
        return False
    if not isinstance(data.get("participants"), list):
        return False
    if not isinstance(data.get("timestamps"), list):
        return False
    return True


def default_facts_payload() -> dict[str, Any]:
    return {
        "statements": [],
        "entities": {
            "mentioned_company": "",
            "product": "",
            "product_version": "",
            "budget": "n/a",
            "competitors": [],
            "industry": "",
            "timeline": "",
            "stakeholders": [],
            "procurement_stage": "",
            "use_case": "",
            "decision_criteria": "",
            "budget_owner": "",
            "implementation_scope": "",
            "custom_fields": {},
        },
        "participants": [],
        "timestamps": [],
    }


def _normalize_scalar_key(s: str) -> str:
    return "".join(c for c in (s or "").lower() if c.isalnum())


def _trim_to_token_budget(text: str, max_tokens: int = MAX_FACTS_INPUT_TOKENS) -> str:
    src = (text or "").strip()
    if not src:
        return ""
    max_chars = max(1, int(max_tokens) * TOKENS_CHAR_RATIO)
    if len(src) <= max_chars:
        return src
    return src[:max_chars].rstrip()


def _split_transcript_chunks(
    transcript: str,
    *,
    chunk_tokens: int = FACTS_CHUNK_TOKENS,
    overlap_tokens: int = FACTS_CHUNK_OVERLAP_TOKENS,
) -> list[str]:
    """
    Sliding-window chunking by approximate token count.
    Keeps overlap to preserve context across boundaries.
    """
    src = (transcript or "").strip()
    if not src:
        return []
    chunk_chars = max(1, int(chunk_tokens) * TOKENS_CHAR_RATIO)
    overlap_chars = max(0, int(overlap_tokens) * TOKENS_CHAR_RATIO)
    step = max(1, chunk_chars - overlap_chars)
    if len(src) <= chunk_chars:
        return [src]

    chunks: list[str] = []
    i = 0
    n = len(src)
    while i < n:
        j = min(n, i + chunk_chars)
        if j < n:
            space = src.rfind(" ", i + int(chunk_chars * 0.6), j)
            if space > i:
                j = space
        chunk = src[i:j].strip()
        if chunk:
            chunks.append(chunk)
        if j >= n:
            break
        i = max(i + step, j - overlap_chars)
    return chunks or [src]


def merge_facts_payloads(payloads: list[dict[str, Any]]) -> dict[str, Any]:
    """Merge fact JSON objects (e.g. LLM facts + heuristic facts)."""
    if not payloads:
        return default_facts_payload()
    if len(payloads) == 1:
        return _normalize_facts_shape(payloads[0])

    base = default_facts_payload()
    # Statements: order-preserving unique
    seen_s: set[str] = set()
    for p in payloads:
        for s in p.get("statements") or []:
            t = str(s).strip()
            if not t:
                continue
            k = t[:512].lower()
            if k not in seen_s:
                seen_s.add(k)
                base["statements"].append(t[:1024])
    if len(base["statements"]) > 80:
        base["statements"] = base["statements"][:80]

    def _vote(key: str) -> str:
        counts: Counter[str] = Counter()
        for p in payloads:
            ent = p.get("entities") if isinstance(p.get("entities"), dict) else {}
            v = str(ent.get(key) or "").strip()
            if v and v.lower() not in ("n/a", "na", "none", "unknown"):
                counts[_normalize_scalar_key(v)] += 1
        if not counts:
            return ""
        winner = max(counts.items(), key=lambda x: (x[1], len(x[0])))[0]
        for p in payloads:
            ent = p.get("entities") if isinstance(p.get("entities"), dict) else {}
            v = str(ent.get(key) or "").strip()
            if v and _normalize_scalar_key(v) == winner:
                return v
        return ""

    ent_out: dict[str, Any] = dict(base["entities"])
    for key in (
        "mentioned_company",
        "product",
        "product_version",
        "industry",
        "use_case",
        "procurement_stage",
    ):
        val = _vote(key)
        if val:
            ent_out[key] = val

    for key in ("timeline", "decision_criteria", "budget_owner", "implementation_scope"):
        best = ""
        for p in payloads:
            ent = p.get("entities") if isinstance(p.get("entities"), dict) else {}
            v = str(ent.get(key) or "").strip()
            if v.lower() in ("n/a", "na", "none", ""):
                continue
            if len(v) > len(best):
                best = v
        if best:
            ent_out[key] = best

    # Budget: max numeric across chunks
    best_b = 0
    for p in payloads:
        ent = p.get("entities") if isinstance(p.get("entities"), dict) else {}
        from app.services.groq_extraction import _coerce_budget

        b = _coerce_budget(ent.get("budget"))
        if b.isdigit():
            best_b = max(best_b, int(b))
    if best_b > 0:
        ent_out["budget"] = best_b
    else:
        ent_out["budget"] = payloads[0].get("entities", {}).get("budget", "n/a") if isinstance(payloads[0].get("entities"), dict) else "n/a"

    comps: list[str] = []
    seen_c: set[str] = set()
    for p in payloads:
        ent = p.get("entities") if isinstance(p.get("entities"), dict) else {}
        for c in ent.get("competitors") or []:
            s = str(c).strip()
            if not s:
                continue
            k = s.lower()
            if k not in seen_c:
                seen_c.add(k)
                comps.append(s)
    ent_out["competitors"] = comps[:32]

    stak: list[str] = []
    seen_st: set[str] = set()
    for p in payloads:
        ent = p.get("entities") if isinstance(p.get("entities"), dict) else {}
        for c in ent.get("stakeholders") or []:
            s = str(c).strip()
            if not s:
                continue
            k = s.lower()
            if k not in seen_st:
                seen_st.add(k)
                stak.append(s)
    ent_out["stakeholders"] = stak[:64]

    cf: dict[str, str] = {}
    for p in payloads:
        ent = p.get("entities") if isinstance(p.get("entities"), dict) else {}
        cfm = ent.get("custom_fields")
        if isinstance(cfm, dict):
            for k, v in cfm.items():
                ks = str(k).strip()
                vs = str(v).strip() if v is not None else ""
                if ks and (ks not in cf or not cf[ks]) and vs:
                    cf[ks[:128]] = vs[:2048]
    ent_out["custom_fields"] = cf

    base["entities"] = ent_out

    parts: list[str] = []
    seen_p: set[str] = set()
    for p in payloads:
        for x in p.get("participants") or []:
            s = str(x).strip()
            if s and s.lower() not in seen_p:
                seen_p.add(s.lower())
                parts.append(s[:512])
    base["participants"] = parts[:64]

    ts_out: list[dict[str, Any]] = []
    for p in payloads:
        for row in p.get("timestamps") or []:
            if isinstance(row, dict):
                ts_out.append(dict(row))
    base["timestamps"] = ts_out[:200]

    return _normalize_facts_shape(base)


def _normalize_facts_shape(data: dict[str, Any]) -> dict[str, Any]:
    out = default_facts_payload()
    if not isinstance(data, dict):
        return out
    stm = data.get("statements")
    if isinstance(stm, list):
        out["statements"] = [str(s).strip()[:1024] for s in stm if str(s).strip()][:80]
    ent = data.get("entities")
    if isinstance(ent, dict):
        for k in _ENT_KEYS_EXPECTED:
            if k not in ent:
                continue
            if k in ("competitors", "stakeholders"):
                if isinstance(ent[k], list):
                    out["entities"][k] = [str(x).strip() for x in ent[k] if str(x).strip()][:32]
            elif k == "custom_fields":
                if isinstance(ent[k], dict):
                    out["entities"][k] = ent[k]
            elif k == "budget":
                out["entities"][k] = ent[k]
            else:
                out["entities"][k] = str(ent[k] or "").strip()[:2048]
    part = data.get("participants")
    if isinstance(part, list):
        out["participants"] = [str(p).strip()[:512] for p in part if str(p).strip()][:64]
    ts = data.get("timestamps")
    if isinstance(ts, list):
        out["timestamps"] = [dict(x) for x in ts if isinstance(x, dict)][:200]
    return out


def _run_single_facts_attempt(prompt: str, *, temperature: float = 0.0) -> tuple[dict[str, Any] | None, bool]:
    if not (settings.groq_model or "").strip():
        return None, False
    try:
        raw = groq_chat_with_retry(
            prompt,
            json_mode=True,
            max_attempts=3,
            temperature=temperature,
            top_p=1.0,
            max_tokens=2048,
        )
    except Exception:
        logger.exception("Groq facts extraction request failed")
        return None, False
    if not raw:
        return None, False
    parsed = _parse_json_loose(raw)
    if not isinstance(parsed, dict):
        return None, False
    if not validate_facts_payload(parsed):
        logger.warning("Facts payload validation failed")
        return None, False
    return _normalize_facts_shape(parsed), True


_SC_AMBIGUOUS_FIELDS: frozenset[str] = frozenset(
    {"budget", "product", "product_version", "timeline", "procurement_stage", "implementation_scope"}
)


def _reconcile_facts_consistency(primary: dict[str, Any], alternate: dict[str, Any]) -> dict[str, Any]:
    """
    Merge two facts payloads with disagreement-aware reconciliation on ambiguous fields.

    - Agreement -> keep primary value.
    - Disagreement -> blank the field (prefer "n/a" + logged).
    - One is "n/a" and the other isn't -> keep the non-empty value.
    - Lists (competitors/stakeholders) -> union via existing merge_facts_payloads.
    """
    merged = merge_facts_payloads([primary, alternate])
    ent_p = primary.get("entities") if isinstance(primary.get("entities"), dict) else {}
    ent_a = alternate.get("entities") if isinstance(alternate.get("entities"), dict) else {}
    ent_m = merged.get("entities") if isinstance(merged.get("entities"), dict) else {}

    def _norm(v: Any) -> str:
        return str(v or "").strip().lower()

    disagreements: list[str] = []
    for f in _SC_AMBIGUOUS_FIELDS:
        vp = ent_p.get(f)
        va = ent_a.get(f)
        np_ = _norm(vp)
        na_ = _norm(va)
        if not np_ and not na_:
            continue
        if np_ in ("n/a", "na", "none") and na_ in ("n/a", "na", "none", ""):
            ent_m[f] = "" if f == "budget" else "n/a"
            continue
        if not np_ or np_ in ("n/a", "na", "none"):
            ent_m[f] = va if isinstance(va, (int, float)) else (str(va) if va is not None else "")
            continue
        if not na_ or na_ in ("n/a", "na", "none"):
            ent_m[f] = vp if isinstance(vp, (int, float)) else (str(vp) if vp is not None else "")
            continue
        if np_ == na_:
            ent_m[f] = vp
            continue
        if f == "budget":
            from app.utils.money_parser import parse_money_to_int

            bp = parse_money_to_int(vp)
            ba = parse_money_to_int(va)
            if bp is not None and ba is not None and bp > 0 and ba > 0:
                ratio = min(bp, ba) / max(bp, ba)
                if ratio >= 0.8:
                    ent_m[f] = bp
                    continue
        disagreements.append(f)
        ent_m[f] = "" if f == "budget" else ""

    if disagreements:
        logger.info("Self-consistency disagreed on %s; blanked.", ", ".join(disagreements))

    merged["entities"] = ent_m
    return merged


def run_facts_extraction(transcript: str) -> dict[str, Any]:
    """
    One or two Groq calls for factual JSON (depending on settings.extraction_self_consistency).
    """
    src = _trim_to_token_budget(transcript, MAX_FACTS_INPUT_TOKENS * 20)
    chunks = _split_transcript_chunks(
        src,
        chunk_tokens=FACTS_CHUNK_TOKENS,
        overlap_tokens=FACTS_CHUNK_OVERLAP_TOKENS,
    )
    if not chunks:
        return default_facts_payload()

    chunk_payloads: list[dict[str, Any]] = []
    for idx, chunk in enumerate(chunks, start=1):
        bounded = _trim_to_token_budget(chunk, MAX_FACTS_INPUT_TOKENS)
        prompt = build_facts_extraction_prompt(bounded)
        parsed, ok = _run_single_facts_attempt(prompt, temperature=0.0)
        if not ok or not parsed:
            logger.warning("Facts extraction failed for chunk %s/%s", idx, len(chunks))
            continue

        if getattr(settings, "extraction_self_consistency", False):
            alt, ok_alt = _run_single_facts_attempt(prompt, temperature=0.2)
            if ok_alt and alt:
                try:
                    parsed = _reconcile_facts_consistency(parsed, alt)
                except Exception:
                    logger.exception("Chunk self-consistency failed; using primary chunk pass")
        chunk_payloads.append(parsed)

    if not chunk_payloads:
        return default_facts_payload()
    return merge_facts_payloads(chunk_payloads)


def heuristics_facts_from_transcript(transcript: str) -> dict[str, Any]:
    """Build a minimal facts object from rule-based entity hints (no LLM)."""
    from app.utils.heuristic_extraction import heuristic_extract_entities

    h = heuristic_extract_entities(transcript)
    ent = {
        "mentioned_company": str(h.get("mentioned_company") or ""),
        "product": str(h.get("product") or ""),
        "product_version": str(h.get("product_version") or ""),
        "budget": h.get("budget") if h.get("budget") not in (None, "") else "n/a",
        "competitors": list(h.get("competitors") or []),
        "industry": str(h.get("industry") or ""),
        "timeline": str(h.get("timeline") or ""),
        "stakeholders": list(h.get("stakeholders") or []),
        "procurement_stage": str(h.get("procurement_stage") or ""),
        "use_case": str(h.get("use_case") or ""),
        "decision_criteria": str(h.get("decision_criteria") or ""),
        "budget_owner": str(h.get("budget_owner") or ""),
        "implementation_scope": str(h.get("implementation_scope") or ""),
        "custom_fields": dict(h.get("custom_fields") or {}),
    }
    lines = [s.strip() for s in re.split(r"(?<=[.!?])\s+", transcript) if len(s.strip()) > 40]
    statements = lines[:24]
    return _normalize_facts_shape(
        {
            "statements": statements,
            "entities": ent,
            "participants": [],
            "timestamps": [],
        }
    )
