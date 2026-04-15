"""
AI Intelligence Layer — classification, scoring, risk detection, summarization,
tagging, normalization, duplicate detection, and email draft generation.

Every public function is self-contained and safe to call independently.
LLM calls go through the existing Groq retry infrastructure; heuristic
fallbacks keep the pipeline running when the API is unavailable.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.utils.groq_retry import groq_chat_with_retry

logger = logging.getLogger(__name__)

_VALID_INTERACTION_TYPES = {"sales", "support", "inquiry", "complaint"}
_VALID_RISK_LEVELS = {"low", "medium", "high"}


# ---------------------------------------------------------------------------
# Internal LLM helpers
# ---------------------------------------------------------------------------

def _llm_json(prompt: str) -> dict | None:
    """Call Groq expecting a JSON object back.  Returns *None* on any failure."""
    try:
        raw = groq_chat_with_retry(prompt, json_mode=True, max_attempts=2)
    except Exception:
        logger.exception("AI Intelligence LLM call failed")
        return None
    if not raw:
        return None
    try:
        text = raw.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
            text = re.sub(r"\s*```\s*$", "", text)
        return json.loads(text)
    except (json.JSONDecodeError, TypeError, ValueError):
        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(raw[start : end + 1])
            except (json.JSONDecodeError, TypeError, ValueError):
                pass
    return None


def _llm_text(prompt: str) -> str:
    """Call Groq expecting a short plain-text answer."""
    try:
        raw = groq_chat_with_retry(prompt, json_mode=False, max_attempts=2)
        return (raw or "").strip()
    except Exception:
        logger.exception("AI Intelligence LLM text call failed")
        return ""


# ---------------------------------------------------------------------------
# 1. classify_interaction
# ---------------------------------------------------------------------------

def classify_interaction(text: str) -> str:
    """Return exactly one of: sales, support, inquiry, complaint."""
    prompt = (
        "You are a strict classifier. Read the conversation and classify it "
        "into EXACTLY one category: sales, support, inquiry, complaint.\n\n"
        "Rules:\n"
        "- sales    = purchasing, pricing, proposals, deals, budget discussions\n"
        "- support  = bugs, issues, broken features, how-to help\n"
        "- inquiry  = general questions, info gathering, demos, evaluations\n"
        "- complaint = frustration, escalation, dissatisfaction, threats to leave\n\n"
        'Return ONLY valid JSON: {"classification": "<category>"}\n'
        "No commentary. No extra keys.\n\n"
        f"Text:\n{text[:8000]}"
    )
    data = _llm_json(prompt)
    if data:
        val = str(data.get("classification", "")).strip().lower()
        if val in _VALID_INTERACTION_TYPES:
            return val

    lower = text.lower()
    if any(w in lower for w in ("price", "buy", "deal", "budget", "proposal", "quote", "purchase", "cost")):
        return "sales"
    if any(w in lower for w in ("broken", "issue", "not working", "bug", "fix", "error", "crash")):
        return "support"
    if any(w in lower for w in ("angry", "frustrated", "terrible", "worst", "unacceptable", "cancel", "lawsuit")):
        return "complaint"
    return "inquiry"


# ---------------------------------------------------------------------------
# 2. score_deal — exact spec scoring
# ---------------------------------------------------------------------------

def score_deal(record: dict[str, Any]) -> int:
    """Return a deal score 0-100 based on structured record fields.

    Scoring logic:
      budget present     → +20
      intent = high      → +30
      intent = medium    → +15
      clear timeline     → +20
      competitors present→ +10
      each missing core field → -5
    """
    score = 0

    budget = str(record.get("budget", "")).strip()
    if budget and budget not in ("0", ""):
        score += 20

    intent = str(record.get("intent", "")).lower()
    if intent == "high":
        score += 30
    elif intent == "medium":
        score += 15

    timeline = str(record.get("timeline", "")).strip()
    if timeline:
        score += 20

    competitors = record.get("competitors", [])
    if isinstance(competitors, list) and len(competitors) > 0:
        score += 10

    missing = 0
    for field in ("budget", "intent", "product", "timeline"):
        val = str(record.get(field, "")).strip()
        if not val:
            missing += 1
    score -= missing * 5

    return max(0, min(100, score))


# ---------------------------------------------------------------------------
# 3. generate_next_action — max 12 words
# ---------------------------------------------------------------------------

def generate_next_action(text: str) -> str:
    """Return a short actionable next step (max 12 words)."""
    prompt = (
        "Read the conversation below and suggest ONE concise next action "
        "for the sales or support team.\n\n"
        "RULES:\n"
        "- Maximum 12 words\n"
        "- Must be actionable (start with a verb)\n"
        "- No JSON, no bullet points, no quotes\n"
        "- Return ONLY the action text\n\n"
        f"Text:\n{text[:6000]}"
    )
    action = _llm_text(prompt)
    if action:
        action = action.strip('"\'.')
        words = action.split()
        return " ".join(words[:12])
    return "Follow up with the contact"


# ---------------------------------------------------------------------------
# 4. detect_risk
# ---------------------------------------------------------------------------

def detect_risk(text: str) -> dict[str, str]:
    """Return {risk_level: low|medium|high, reason: '...'}."""
    prompt = (
        "Analyze the conversation for deal or customer risk.\n\n"
        "Risk factors: competitor mentions, budget objections, delays, "
        "complaints, negative sentiment, missing decision-maker, "
        "churn signals, legal threats.\n\n"
        'Return ONLY valid JSON: {"risk_level": "low|medium|high", "reason": "short explanation"}\n'
        "No extra keys. No commentary.\n\n"
        f"Text:\n{text[:6000]}"
    )
    data = _llm_json(prompt)
    if data:
        level = str(data.get("risk_level", "")).strip().lower()
        reason = str(data.get("reason", "")).strip()
        if level in _VALID_RISK_LEVELS:
            return {"risk_level": level, "reason": reason[:512]}

    lower = text.lower()
    if any(w in lower for w in ("cancel", "leave", "terrible", "worst", "lawsuit", "unacceptable")):
        return {"risk_level": "high", "reason": "Negative sentiment detected"}
    if any(w in lower for w in ("competitor", "alternative", "delay", "budget concern", "expensive")):
        return {"risk_level": "medium", "reason": "Potential churn signals detected"}
    return {"risk_level": "low", "reason": "No significant risk signals"}


# ---------------------------------------------------------------------------
# 5. generate_summary — 2 concise lines
# ---------------------------------------------------------------------------

def generate_summary(text: str) -> str:
    """Return a 2-line concise summary."""
    prompt = (
        "Summarize this conversation in exactly 2 concise sentences.\n\n"
        "Focus on:\n"
        "1. What the customer needs or discussed\n"
        "2. Key outcome or decision\n\n"
        "Return ONLY the 2 sentences. No labels, no JSON.\n\n"
        f"Text:\n{text[:8000]}"
    )
    summary = _llm_text(prompt)
    return summary[:1024] if summary else "No summary available."


# ---------------------------------------------------------------------------
# 6. auto_tag
# ---------------------------------------------------------------------------

def auto_tag(text: str) -> list[str]:
    """Return a list of relevant CRM tags (max 8)."""
    prompt = (
        "Analyze the conversation and return relevant CRM tags.\n\n"
        'Return ONLY valid JSON: {"tags": ["tag1", "tag2"]}\n'
        "Possible tags: urgent, enterprise, small-business, follow-up, "
        "demo-request, pricing, technical, renewal, upsell, new-lead, "
        "escalation, decision-maker, budget-approved, competitor-mentioned.\n"
        "Only include tags that genuinely apply. Max 8 tags.\n"
        "No extra keys.\n\n"
        f"Text:\n{text[:6000]}"
    )
    data = _llm_json(prompt)
    if data:
        tags = data.get("tags", [])
        if isinstance(tags, list):
            return [str(t).strip().lower() for t in tags if str(t).strip()][:8]

    tags: list[str] = []
    lower = text.lower()
    if any(w in lower for w in ("urgent", "asap", "immediately")):
        tags.append("urgent")
    if any(w in lower for w in ("enterprise", "large-scale", "company-wide")):
        tags.append("enterprise")
    if any(w in lower for w in ("demo", "demonstration", "trial")):
        tags.append("demo-request")
    if any(w in lower for w in ("price", "pricing", "cost", "quote")):
        tags.append("pricing")
    if any(w in lower for w in ("competitor", "alternative")):
        tags.append("competitor-mentioned")
    return tags or ["general"]


# ---------------------------------------------------------------------------
# 7. normalize_data
# ---------------------------------------------------------------------------

def normalize_data(record: dict[str, Any]) -> dict[str, Any]:
    """Normalize budget and timeline values in-place and return the record."""
    budget_raw = str(record.get("budget", "")).strip()
    if budget_raw:
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
    if timeline_raw:
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
    """Check if a similar company or contact already exists.

    Returns {is_duplicate: bool, matches: [{id, name, similarity}]}.
    """
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
# 9. generate_email_draft
# ---------------------------------------------------------------------------

def generate_email_draft(record: dict[str, Any]) -> str:
    """Return a short follow-up email draft based on record context."""
    context_parts = []
    for key in ("product", "budget", "timeline", "intent", "industry", "mentioned_company"):
        val = str(record.get(key, "")).strip()
        if val:
            context_parts.append(f"{key}: {val}")
    context_str = "\n".join(context_parts) if context_parts else "General inquiry"

    prompt = (
        "Write a short, professional follow-up email (3-5 sentences) based on "
        "the CRM record context below. Be warm but concise. "
        "Include a clear call to action. Return ONLY the email body text.\n\n"
        f"Context:\n{context_str}"
    )
    draft = _llm_text(prompt)
    if draft:
        return draft[:2048]
    return (
        "Thank you for your time. I wanted to follow up on our recent conversation. "
        "Please let me know if you have any questions or would like to schedule "
        "a follow-up call. Looking forward to hearing from you."
    )


# ---------------------------------------------------------------------------
# Batch helper — run all intelligence in one call for the pipeline
# ---------------------------------------------------------------------------

def run_ai_intelligence(
    text: str,
    extracted: dict[str, Any],
) -> dict[str, Any]:
    """Run all AI intelligence functions and return a consolidated result dict.

    This is the single entry-point used by the ingestion pipeline.
    """
    normalized = normalize_data(dict(extracted))

    interaction_type = classify_interaction(text)
    deal_score_val = score_deal(normalized)
    risk = detect_risk(text)
    summary = generate_summary(text)
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
