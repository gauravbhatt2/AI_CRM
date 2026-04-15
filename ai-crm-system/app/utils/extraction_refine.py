"""
Post-process LLM extraction: fix weak `product` values; backfill `timeline` when cues exist.

HubSpot and CRM "Product" lines need a human commercial description, not internal
version strings like "map update version 7.7".
"""

from __future__ import annotations

import re
from typing import Any


def infer_timeline_hint(transcript: str) -> str | None:
    """
    Short CRM timeline phrase from plain transcript (used by heuristics + post-merge refine).
    Covers same-day / urgency language the LLM sometimes omits.
    """
    t = (transcript or "").strip()
    if not t:
        return None
    s = t.lower()
    if re.search(r"\bgo\s*live\b", s):
        return "Go-live mentioned"
    if re.search(
        r"(?:ship(?:ped|ping|s)?\s+out\s+today|ship\s+today|ships?\s+today|"
        r"it'?ll\s+ship\s+out\s+today)",
        s,
    ):
        return "Today - shipping / fulfillment discussed"
    if re.search(
        r"(?:purchasing\s+today|reasons\s+to\s+consider\s+purchasing\s+today|"
        r"set\s+this\s+order\s+up\s+for\s+you\s+now)",
        s,
    ):
        return "Today - ordering / urgency"
    if re.search(
        r"\b(?:Q[1-4]\s*20\d{2}|next\s+quarter|this\s+quarter)\b",
        s,
    ):
        m = re.search(r"\b(Q[1-4]\s*20\d{2}|next\s+quarter|this\s+quarter)\b", s, re.I)
        return (m.group(1) or "Quarter timeframe").strip()
    if re.search(r"\b(?:next|this)\s+week\b", s):
        m = re.search(r"\b((?:next|this)\s+week)\b", s, re.I)
        return m.group(1).title() if m else "This week"
    if re.search(
        r"\bwithin\s+\d+\s*(?:days|weeks|months)\b",
        s,
    ):
        return "Relative deadline mentioned"
    if re.search(r"\b(?:asap|a\.s\.a\.p\.|as\s+soon\s+as)\b", s):
        return "ASAP"
    if re.search(r"(?:before\s+it\s+expires|promotion.{0,40}expires?)", s) and re.search(
        r"\b(today|soon|limited)\b",
        s,
    ):
        return "Promotion / expiry window"
    return None


def refine_timeline_core_field(norm: dict[str, Any], transcript: str = "") -> None:
    """If the model left `timeline` empty, fill from transcript cues."""
    if not isinstance(norm, dict):
        return
    if str(norm.get("timeline") or "").strip():
        return
    hint = infer_timeline_hint(transcript)
    if hint:
        norm["timeline"] = hint


def _map_like_weak_product(product: str) -> bool:
    """True when product is empty or looks like a map/version label, not a real SKU description."""
    p = (product or "").strip().lower()
    if not p:
        return True
    if re.match(r"^map\s+update(?:\s+version\s*[\d.]+)?\s*$", p):
        return True
    if re.match(r"^v?[\d.]+\s*$", p):
        return True
    if "map" in p and "version" in p and len(p) <= 48:
        return True
    if "map update" in p and re.search(r"\d+\.\d+", p) and len(p) <= 56:
        return True
    return False


def _automotive_map_context(norm: dict[str, Any], transcript: str) -> bool:
    """True when conversation + custom_fields suggest in-dash / OEM map update."""
    cf = norm.get("custom_fields")
    if isinstance(cf, dict) and any(
        str(cf.get(k) or "").strip()
        for k in ("vehicle_make", "vehicle_model", "vehicle_year")
    ):
        return True
    t = (transcript or "").lower()
    return bool(
        ("map" in t and "car" in t)
        or ("map" in t and "vehicle" in t)
        or ("navigation" in t and "map" in t)
        or ("update the map" in t)
    )


def refine_product_core_field(norm: dict[str, Any], transcript: str = "") -> None:
    """
    Replace version-heavy `product` strings with a clear commercial label when appropriate.

    Mutates `norm` in place (same pattern as Groq normalize merge).
    """
    if not isinstance(norm, dict):
        return
    product = str(norm.get("product") or "").strip()
    if not _map_like_weak_product(product):
        return
    if not _automotive_map_context(norm, transcript):
        return

    cf = norm.get("custom_fields")
    if not isinstance(cf, dict):
        cf = {}
    vy = str(cf.get("vehicle_year") or "").strip()
    vmk = str(cf.get("vehicle_make") or "").strip()
    vmd = str(cf.get("vehicle_model") or "").strip()
    vehicle = " ".join(x for x in (vy, vmk, vmd) if x).strip()

    if vehicle:
        norm["product"] = f"In-dash navigation map update - {vehicle}"
    else:
        norm["product"] = "In-dash navigation map database update"


def enrich_map_version_custom_field(norm: dict[str, Any], transcript: str = "") -> None:
    """Store map software version in custom_fields when the transcript states it but the LLM omitted it."""
    if not isinstance(norm, dict):
        return
    if not _automotive_map_context(norm, transcript):
        return
    cf = norm.get("custom_fields")
    if not isinstance(cf, dict):
        cf = {}
        norm["custom_fields"] = cf
    if str(cf.get("map_version") or "").strip():
        return
    from app.utils.hubspot_product import extract_map_version_from_transcript

    v = extract_map_version_from_transcript(transcript)
    if v:
        cf["map_version"] = v
