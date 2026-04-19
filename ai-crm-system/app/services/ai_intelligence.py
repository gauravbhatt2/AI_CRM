"""
AI Intelligence Layer — classification, scoring, risk detection, summarization,
and tagging.

Primary signals come from the unified extraction LLM (`groq_extraction`). This
module provides deterministic heuristics as fallback when the unified call is
unavailable or incomplete. No Groq calls are made from this file.
"""

from __future__ import annotations

import re
from typing import Any

from app.utils.budget import parse_budget_to_int
from app.utils.extraction_refine import infer_budget_hint, infer_product_hint

_VALID_INTERACTION_TYPES = {"sales", "support", "inquiry", "complaint"}
_VALID_RISK_LEVELS = {"low", "medium", "high"}


def _is_placeholder(value: str) -> bool:
    s = (value or "").strip().lower()
    return s in ("", "n/a", "na", "none", "null", "unknown")


# ---------------------------------------------------------------------------
# 1. classify_interaction (heuristic)
# ---------------------------------------------------------------------------


def classify_interaction(text: str) -> str:
    """Return exactly one of: sales, support, inquiry, complaint."""
    lower = text.lower()
    if any(w in lower for w in ("angry", "frustrated", "terrible", "worst", "unacceptable", "cancel", "lawsuit")):
        return "complaint"
    if any(w in lower for w in ("broken", "issue", "not working", "bug", "fix", "error", "crash")):
        return "support"
    if any(w in lower for w in ("price", "buy", "deal", "budget", "proposal", "quote", "purchase", "cost")):
        return "sales"
    return "inquiry"


# ---------------------------------------------------------------------------
# 2. score_deal
# ---------------------------------------------------------------------------


def score_deal(record: dict[str, Any]) -> int:
    """Return a deal score 0-100 based on structured record fields."""
    score = 0

    budget = parse_budget_to_int(str(record.get("budget", "")).strip())
    if budget > 0:
        score += 20

    intent = str(record.get("intent", "")).lower()
    if intent == "high":
        score += 30
    elif intent == "medium":
        score += 15

    timeline = str(record.get("timeline", "")).strip()
    if timeline and not _is_placeholder(timeline):
        score += 20

    competitors = record.get("competitors", [])
    if isinstance(competitors, list) and len(competitors) > 0:
        score += 10

    missing = 0
    for field in ("budget", "intent", "product", "timeline"):
        val = str(record.get(field, "")).strip()
        if not val or _is_placeholder(val):
            missing += 1
    score -= missing * 5

    return max(0, min(100, score))


# ---------------------------------------------------------------------------
# 3. generate_next_action
# ---------------------------------------------------------------------------


def generate_next_action(text: str) -> str:
    """Return a short actionable next step (max 12 words)."""
    lower = text.lower()
    if "demo" in lower and ("next week" in lower or "early next week" in lower):
        return "Schedule detailed demo with stakeholders early next week"
    if "follow up" in lower:
        return "Send follow-up with proposed times and required attendees"
    return "Follow up with the contact"


# ---------------------------------------------------------------------------
# 4. detect_risk
# ---------------------------------------------------------------------------


def detect_risk(text: str) -> dict[str, str]:
    """Return {risk_level: low|medium|high, reason: '...'}."""
    lower = text.lower()
    budget_pushback = any(
        w in lower for w in ("not sure i can afford", "can't afford", "cannot afford", "too expensive", "budget concern")
    )
    purchase_signal = any(
        w in lower for w in ("let's go ahead", "use a visa", "place this order", "credit card", "purchase today")
    )
    if any(w in lower for w in ("cancel", "leave", "terrible", "worst", "lawsuit", "unacceptable")):
        return {"risk_level": "high", "reason": "Negative sentiment detected"}
    if budget_pushback and purchase_signal:
        return {"risk_level": "medium", "reason": "Budget hesitation surfaced despite later purchase intent"}
    competitor_pressure = any(
        w in lower
        for w in ("competitor", "alternative", "salesforce", "other tools", "other vendors", "evaluating")
    )
    timeline_risk = any(w in lower for w in ("implementation time", "takes too long", "go live"))
    if budget_pushback or competitor_pressure or timeline_risk:
        return {"risk_level": "medium", "reason": "Potential objection or churn signal detected"}
    if purchase_signal:
        return {"risk_level": "low", "reason": "Positive buying intent and checkout progression"}
    return {"risk_level": "low", "reason": "No significant risk signals"}


# ---------------------------------------------------------------------------
# 5. generate_summary
# ---------------------------------------------------------------------------


def generate_summary(text: str, extracted: dict[str, Any] | None = None) -> str:
    """Return a concise 2-3 sentence summary (heuristic)."""
    low = text.lower()
    ex = extracted if isinstance(extracted, dict) else {}
    company = str(ex.get("mentioned_company") or "").strip()
    product = str(ex.get("product") or "").strip() or infer_product_hint(text) or "requested product/service"
    budget = infer_budget_hint(text)
    if not budget:
        b2 = str(ex.get("budget") or "").strip()
        budget = b2 if b2 else None
    timeline = str(ex.get("timeline") or "").strip()
    next_step = str(ex.get("next_step") or "").strip()
    competitors = ex.get("competitors") if isinstance(ex.get("competitors"), list) else []
    pain_points = str(ex.get("pain_points") or "").strip()
    vehicle = ""
    vm = re.search(r"\b(20\d{2}|19\d{2})\s+([A-Z][a-zA-Z]+)\s+([A-Z][a-zA-Z0-9]+)\b", text)
    if vm:
        vehicle = f"{vm.group(1)} {vm.group(2)} {vm.group(3)}"
    version = ""
    ver = re.search(r"\bversion\s+([0-9]+(?:\.[0-9]+)*)\b", low)
    if ver:
        version = ver.group(1)

    affordability = any(
        x in low for x in ("can't afford", "cannot afford", "not really sure if i can afford", "too expensive")
    )
    close_signal = any(
        x in low for x in ("let's go ahead", "use a visa", "credit card", "place this order", "set this order up")
    )

    s1_parts: list[str] = []
    if company:
        s1_parts.append(f"{company} discusses")
    else:
        s1_parts.append("Prospect discusses")
    s1_parts.append(product)
    if vehicle:
        s1_parts.append(f"for a {vehicle}")
    if version:
        s1_parts.append(f"and discusses version {version}")
    if budget:
        s1_parts.append(f"with budget around {budget}")
    s1 = " ".join(s1_parts).strip()
    s1 = re.sub(r"\s+", " ", s1).rstrip(" .") + "."

    if affordability and close_signal:
        s2 = "Customer raises affordability concerns but proceeds to place the order by card."
    elif close_signal:
        s2 = "Conversation progresses to checkout with payment details and immediate fulfillment discussed."
    elif affordability:
        s2 = "Conversation surfaces affordability concerns and needs follow-up before purchase confirmation."
    elif next_step and not _is_placeholder(next_step):
        s2 = f"Next step is {next_step.lower().strip('.')}."
    elif "demo" in low and "next week" in low:
        s2 = "Next step is a detailed demo with the team early next week."
    elif timeline and not _is_placeholder(timeline):
        s2 = f"Target timeline is {timeline.lower().strip('.')} with evaluation in progress."
    elif competitors:
        s2 = "Prospect is comparing alternatives and requires stronger differentiation."
    else:
        s2 = "Conversation captures pricing and support details with follow-up pending confirmation."
    s3 = ""
    if timeline and not _is_placeholder(timeline):
        s3 = f"Expected implementation timeline is {timeline.lower().strip('.')}."
    elif pain_points and not _is_placeholder(pain_points):
        s3 = f"Key pain points include {pain_points.lower().strip('.')}."
    elif competitors:
        s3 = f"Competitor context includes {', '.join(str(c) for c in competitors[:2])}."

    joined = f"{s1} {s2}" if not s3 else f"{s1} {s2} {s3}"
    return joined[:1024]


# ---------------------------------------------------------------------------
# 6. auto_tag
# ---------------------------------------------------------------------------


def auto_tag(text: str) -> list[str]:
    """Return a list of relevant CRM tags (max 8)."""
    tags: list[str] = []
    lower = text.lower()
    if any(w in lower for w in ("urgent", "asap", "immediately", "today", "right away")):
        tags.append("urgent")
    if any(w in lower for w in ("enterprise", "large-scale", "company-wide")):
        tags.append("enterprise")
    if any(w in lower for w in ("small business", "startup", "small team")):
        tags.append("small-business")
    if any(w in lower for w in ("demo", "demonstration", "trial")):
        tags.append("demo-request")
    if any(w in lower for w in ("price", "pricing", "cost", "quote")):
        tags.append("pricing")
    if any(w in lower for w in ("follow up", "follow-up", "call back", "check back")):
        tags.append("follow-up")
    if any(w in lower for w in ("technical", "bug", "issue", "integration", "api")):
        tags.append("technical")
    if any(w in lower for w in ("map update", "navigation", "version")):
        tags.append("technical")
    if any(w in lower for w in ("renew", "renewal", "contract extension")):
        tags.append("renewal")
    if any(w in lower for w in ("upsell", "upgrade", "add-on", "additional seats")):
        tags.append("upsell")
    if any(w in lower for w in ("new lead", "first call", "new prospect")):
        tags.append("new-lead")
    if any(w in lower for w in ("escalat", "complaint", "unacceptable", "angry")):
        tags.append("escalation")
    if any(w in lower for w in ("ceo", "cto", "cfo", "director", "vp", "head of", "decision maker")):
        tags.append("decision-maker")
    if any(w in lower for w in ("budget approved", "approved budget", "budget signoff", "budget signed off")):
        tags.append("budget-approved")
    if any(w in lower for w in ("use a visa", "credit card", "place this order", "set this order up")):
        tags.append("budget-approved")
    if any(w in lower for w in ("competitor", "alternative")):
        tags.append("competitor-mentioned")
    deduped: list[str] = []
    for t in tags:
        if t not in deduped:
            deduped.append(t)
    return deduped[:8] or ["general"]


# ---------------------------------------------------------------------------
# 7. normalize_data
# ---------------------------------------------------------------------------


def normalize_data(record: dict[str, Any]) -> dict[str, Any]:
    """Normalize budget and timeline values in-place and return the record."""
    budget_raw = str(record.get("budget", "")).strip()
    if budget_raw and not _is_placeholder(budget_raw):
        cleaned = re.sub(r"[,$£€\s]", "", budget_raw)
        m = re.match(r"^(\d+(?:\.\d+)?)([kKmM])?$", cleaned)
        if m:
            num = float(m.group(1))
            suffix = (m.group(2) or "").lower()
            if suffix == "k":
                num *= 1_000
            elif suffix == "m":
                num *= 1_000_000
            record["budget"] = str(int(num))

    timeline_raw = str(record.get("timeline", "")).strip().lower()
    if timeline_raw and not _is_placeholder(timeline_raw):
        timeline_map = {
            "q1": "Q1 (Jan-Mar)",
            "q2": "Q2 (Apr-Jun)",
            "q3": "Q3 (Jul-Sep)",
            "q4": "Q4 (Oct-Dec)",
            "eoy": "End of Year",
            "eom": "End of Month",
            "asap": "ASAP",
        }
        for abbr, full in timeline_map.items():
            if timeline_raw == abbr:
                record["timeline"] = full
                break

    return record


# ---------------------------------------------------------------------------
# 8. detect_duplicates
# ---------------------------------------------------------------------------


def detect_duplicates(
    record: dict[str, Any],
    db: Any,
) -> dict[str, Any]:
    """Check if a similar company or contact already exists."""
    from sqlalchemy import select, func

    from app.db.models import Account, Contact

    matches: list[dict] = []
    company_name = str(record.get("company", "") or record.get("mentioned_company", "")).strip()
    contact_name = str(record.get("contact_name", "")).strip()

    if company_name:
        rows = db.scalars(
            select(Account).where(
                func.lower(Account.name).contains(company_name.lower()[:256])
            )
        ).all()
        for row in rows[:5]:
            matches.append({"type": "account", "id": row.id, "name": row.name})

    if contact_name:
        rows = db.scalars(
            select(Contact).where(
                func.lower(Contact.name).contains(contact_name.lower()[:256])
            )
        ).all()
        for row in rows[:5]:
            matches.append({"type": "contact", "id": row.id, "name": row.name})

    return {"is_duplicate": len(matches) > 0, "matches": matches}


# ---------------------------------------------------------------------------
# 9. generate_email_draft (template fallback only)
# ---------------------------------------------------------------------------


def generate_email_draft(record: dict[str, Any]) -> str:
    """Return a short follow-up email draft based on record context (no LLM)."""
    product = str(record.get("product", "") or "").strip()
    company = str(record.get("mentioned_company", "") or "").strip()
    if product or company:
        ctx = ", ".join(x for x in (company, product) if x)
        return (
            f"Thank you for discussing {ctx}. I wanted to follow up with any open questions "
            "and offer a brief next call to align on timelines. Please reply with a time that works."
        )[:2048]
    return (
        "Thank you for your time. I wanted to follow up on our recent conversation. "
        "Please let me know if you have any questions or would like to schedule "
        "a follow-up call. Looking forward to hearing from you."
    )


# ---------------------------------------------------------------------------
# Batch helper — used by ingestion; merges unified LLM output when provided
# ---------------------------------------------------------------------------


def run_ai_intelligence(
    text: str,
    extracted: dict[str, Any],
    *,
    llm_primary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Consolidated intelligence for the pipeline (heuristics fill gaps)."""
    normalized = normalize_data(dict(extracted))

    if llm_primary and isinstance(llm_primary, dict):
        interaction_type = str(llm_primary.get("interaction_type") or "").strip().lower()
        if interaction_type not in _VALID_INTERACTION_TYPES:
            interaction_type = classify_interaction(text)

        try:
            deal_score_val = int(llm_primary.get("deal_score", 0))
        except (TypeError, ValueError):
            deal_score_val = score_deal(normalized)
        deal_score_val = max(0, min(100, deal_score_val))

        risk_level = str(llm_primary.get("risk_level") or "").strip().lower()
        if risk_level not in _VALID_RISK_LEVELS:
            risk = detect_risk(text)
            risk_level = risk["risk_level"]
            risk_reason = risk["reason"]
        else:
            risk_reason = str(llm_primary.get("risk_reason") or "").strip()
            if _is_placeholder(risk_reason):
                risk_reason = detect_risk(text)["reason"]

        summary = str(llm_primary.get("summary") or "").strip()
        if _is_placeholder(summary):
            summary = generate_summary(text, normalized)

        next_action = str(llm_primary.get("next_action") or "").strip().strip('"\'')
        if _is_placeholder(next_action):
            next_action = generate_next_action(text)
        words = next_action.split()
        if len(words) > 12:
            next_action = " ".join(words[:12])

        tags_raw = llm_primary.get("tags")
        if isinstance(tags_raw, list) and tags_raw:
            tags = [str(t).strip().lower().replace(" ", "-") for t in tags_raw if str(t).strip()][:8]
        else:
            tags = auto_tag(text)

        return {
            "interaction_type": interaction_type,
            "deal_score": deal_score_val,
            "risk_level": risk_level,
            "risk_reason": risk_reason[:2048],
            "summary": summary[:4096],
            "tags": tags,
            "next_action": next_action[:2048],
        }

    interaction_type = classify_interaction(text)
    deal_score_val = score_deal(normalized)
    risk = detect_risk(text)
    summary = generate_summary(text, normalized)
    tags = auto_tag(text)
    next_action = generate_next_action(text)

    return {
        "interaction_type": interaction_type,
        "deal_score": deal_score_val,
        "risk_level": risk["risk_level"],
        "risk_reason": risk["reason"],
        "summary": summary,
        "tags": tags,
        "next_action": next_action,
    }
