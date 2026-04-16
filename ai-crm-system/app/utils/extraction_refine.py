"""
Post-process LLM extraction: fix weak `product` values; backfill `timeline` when cues exist.

HubSpot and CRM "Product" lines need a human commercial description, not internal
version strings like "map update version 7.7".
"""

from __future__ import annotations

import re
from typing import Any


def _money_to_int(text: str, suffix: str = "") -> str:
    raw = (text or "").strip()
    if not raw:
        return ""
    cleaned = re.sub(r"[,$₹€\s]", "", raw)
    if not cleaned:
        return ""
    try:
        val = float(cleaned)
    except ValueError:
        return ""
    s = (suffix or "").strip().lower()
    if s == "k":
        val *= 1_000
    elif s == "m":
        val *= 1_000_000
    return str(max(0, int(round(val))))


def _correct_consumer_map_price_noise(transcript: str, amount: int) -> int:
    """
    Correct likely ASR thousands-comma inflation for consumer map update calls.

    Example noisy ASR: "$99,000" where call context clearly indicates "$99".
    """
    if amount <= 0:
        return amount
    s = (transcript or "").lower()
    map_ctx = ("map" in s) and any(k in s for k in ("vehicle", "car", "nissan", "honda", "altima"))
    promo_ctx = any(
        k in s for k in ("$50 off", "50 off", "shipping and tax", "ship out today", "credit card", "version")
    )
    if map_ctx and promo_ctx and amount >= 10_000 and amount % 1000 == 0:
        shrunk = amount // 1000
        if 20 <= shrunk <= 500:
            return shrunk
    return amount


def infer_budget_hint(transcript: str) -> str | None:
    """
    Infer a conservative numeric budget from transcript.

    Avoids over-scaling plain values such as '99 dollars' into thousands.
    """
    t = (transcript or "").strip()
    if not t:
        return None

    # Budget-specific context first.
    ctx = re.search(
        r"\bbudget\b.{0,40}?([₹$€]?\s*\d+(?:[.,]\d+)?)(?:\s*([kKmM]))?",
        t,
        flags=re.I,
    )
    if ctx:
        amount = _money_to_int(ctx.group(1), ctx.group(2) or "")
        if amount:
            return str(_correct_consumer_map_price_noise(t, int(amount)))

    # Explicit currency amount.
    cur = re.search(
        r"(?:₹|\$|€|usd|inr)\s*(\d+(?:[.,]\d+)?)(?:\s*([kKmM]))?\b",
        t,
        flags=re.I,
    )
    if cur:
        amount = _money_to_int(cur.group(1), cur.group(2) or "")
        if amount:
            return str(_correct_consumer_map_price_noise(t, int(amount)))

    # Number with explicit k/m suffix.
    short = re.search(r"\b(\d+(?:[.,]\d+)?)\s*([kKmM])\b", t)
    if short:
        amount = _money_to_int(short.group(1), short.group(2))
        if amount:
            return amount

    return None


def infer_company_hint(transcript: str) -> str | None:
    """Infer company name from common phrases, with cleanup."""
    t = (transcript or "").strip()
    if not t:
        return None
    patterns = (
        r"\bfrom\s+([A-Z][A-Za-z0-9&.'-]+(?:\s+[A-Z][A-Za-z0-9&.'-]+){0,5})",
        r"\bat\s+([A-Z][A-Za-z0-9&.'-]+(?:\s+[A-Z][A-Za-z0-9&.'-]+){0,5})",
        r"\bcompany(?:\s+name)?\s*(?:is|:)\s*([A-Z][A-Za-z0-9&.'-]+(?:\s+[A-Z][A-Za-z0-9&.'-]+){0,5})",
    )
    stop = {"The", "A", "An", "Team", "Support", "Sales", "Client", "Customer"}
    trailing = {"is", "from", "the", "company", "inc", "llc"}
    for p in patterns:
        m = re.search(p, t)
        if not m:
            continue
        name = " ".join(m.group(1).strip().split())
        parts = [x for x in name.split() if x not in stop]
        while parts and parts[-1].lower().strip(".,;:") in trailing:
            parts.pop()
        cleaned = " ".join(parts).strip(" ,.;:-")
        if len(cleaned) >= 2:
            return cleaned
    return None


def infer_product_hint(transcript: str) -> str | None:
    """Infer product/service phrase from simple sales language."""
    t = (transcript or "").strip()
    if not t:
        return None
    # Domain-specific canonical product first.
    if re.search(r"\b(?:update|updat(?:e|ing)).{0,24}\bmap\b", t, re.I) and re.search(
        r"\b(?:car|vehicle|navigation|nissan|honda|toyota|ford)\b",
        t,
        re.I,
    ):
        return "In-dash navigation map update"

    m = re.search(
        r"\b(?:interested in|looking for|need|needs|evaluate|evaluating|buying)\s+([A-Za-z0-9][A-Za-z0-9\s&+./-]{3,80})",
        t,
        flags=re.I,
    )
    if m:
        phrase = m.group(1).strip(" .,:;")
        phrase = re.split(
            r"\b(?:for|with|because|by|this|that|and|but|if|when|timeline|budget)\b",
            phrase,
            maxsplit=1,
            flags=re.I,
        )[0].strip(" .,:;")
        banned = (
            "customer number",
            "phone number",
            "address",
            "credit card",
            "visa",
            "profile",
        )
        if any(b in phrase.lower() for b in banned):
            phrase = ""
        if len(phrase) >= 3:
            return phrase
    if re.search(r"\bmap\s+update\b", t, re.I):
        return "In-dash navigation map update"
    return None


def infer_industry_hint(transcript: str) -> str | None:
    """Infer industry from explicit domain keywords."""
    t = (transcript or "").lower()
    if not t:
        return None
    mapping = (
        ("automotive", ("automotive", "vehicle", "car", "dealership")),
        ("healthcare", ("healthcare", "hospital", "clinic", "patient")),
        ("finance", ("bank", "banking", "fintech", "insurance")),
        ("retail", ("retail", "ecommerce", "e-commerce", "store")),
        ("education", ("education", "school", "university", "student")),
        ("manufacturing", ("manufacturing", "factory", "plant", "supply chain")),
        ("real estate", ("real estate", "property", "brokerage")),
        ("technology", ("saas", "software", "platform", "api")),
    )
    for industry, terms in mapping:
        if any(term in t for term in terms):
            return industry
    return None


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


def refine_budget_core_field(norm: dict[str, Any], transcript: str = "") -> None:
    """Backfill budget and correct obvious scaling mistakes using transcript evidence."""
    if not isinstance(norm, dict):
        return
    inferred = infer_budget_hint(transcript)
    cur_raw = str(norm.get("budget") or "").strip()
    if not cur_raw:
        if inferred:
            norm["budget"] = inferred
        return
    cur_digits = re.sub(r"[^\d]", "", cur_raw)
    if not cur_digits:
        if inferred:
            norm["budget"] = inferred
        return
    if inferred:
        try:
            cur_i = int(cur_digits)
            inf_i = int(inferred)
        except ValueError:
            return
        # Prefer transcript-native value when LLM likely over-inflated (e.g. 99 -> 99000).
        if inf_i > 0 and cur_i >= 1000 and cur_i % 1000 == 0 and inf_i < 1000:
            norm["budget"] = inferred
            return
    norm["budget"] = cur_digits


def refine_company_core_field(norm: dict[str, Any], transcript: str = "") -> None:
    """Backfill or clean mentioned_company with transcript evidence."""
    if not isinstance(norm, dict):
        return
    current = str(norm.get("mentioned_company") or "").strip(" ,.;:-")
    if current and len(current) >= 2 and len(current.split()) <= 8:
        norm["mentioned_company"] = current
        return
    hint = infer_company_hint(transcript)
    if hint:
        norm["mentioned_company"] = hint


def refine_product_industry_fields(norm: dict[str, Any], transcript: str = "") -> None:
    """Backfill product and industry when LLM returns empty values."""
    if not isinstance(norm, dict):
        return
    if not str(norm.get("product") or "").strip():
        p = infer_product_hint(transcript)
        if p:
            norm["product"] = p
    if not str(norm.get("industry") or "").strip():
        i = infer_industry_hint(transcript)
        if i:
            norm["industry"] = i


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
