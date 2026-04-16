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
from app.utils.budget import parse_budget_to_int
from app.utils.extraction_refine import infer_budget_hint, infer_product_hint

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
        "Classify the conversation into EXACTLY one label: sales, support, inquiry, complaint.\n"
        "The transcript may come from Whisper ASR and contain noise.\n\n"
        "Decision rubric:\n"
        "- complaint: explicit dissatisfaction, escalation, refund/cancel threats, legal tone.\n"
        "- support: troubleshooting, break/fix, bug/error, technical help requests.\n"
        "- sales: pricing, proposal, procurement, contract, budget, purchase intent.\n"
        "- inquiry: informational discussion without clear support issue or buying motion.\n\n"
        "Tie-break order when multiple labels appear: complaint > support > sales > inquiry.\n"
        "Use strongest dominant intent in the latest part of the conversation.\n"
        "Ignore filler words and transcription artifacts.\n\n"
        'Return ONLY JSON: {"classification": "sales|support|inquiry|complaint"}\n'
        "No extra keys. No explanation.\n\n"
        f"Conversation:\n{text[:8000]}"
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

    budget = parse_budget_to_int(str(record.get("budget", "")).strip())
    if budget > 0:
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
        "Suggest ONE highest-impact next action for the internal team.\n"
        "The transcript may be noisy ASR text.\n\n"
        "Rules:\n"
        "- Maximum 12 words.\n"
        "- Start with an imperative verb (e.g., Schedule, Send, Confirm, Escalate).\n"
        "- Must be concrete and directly grounded in the conversation outcome.\n"
        "- If no clear action is stated, output: \"Follow up to clarify next steps\"\n"
        "- Output plain text only. No quotes, bullets, or JSON.\n\n"
        f"Conversation:\n{text[:6000]}"
    )
    action = _llm_text(prompt)
    if action:
        action = action.strip('"\'.')
        words = action.split()
        return " ".join(words[:12])
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
    prompt = (
        "Assess deal/customer risk from the conversation.\n"
        "Treat the transcript as noisy ASR and focus on clear signals.\n\n"
        "Risk scale:\n"
        "- high: churn/cancel threat, legal escalation, severe dissatisfaction, hard blocker.\n"
        "- medium: competitor pressure, budget pushback, timeline slippage, unclear ownership.\n"
        "- low: cooperative tone with no significant blockers.\n\n"
        "Reason requirements:\n"
        "- 8-20 words.\n"
        "- Mention the strongest explicit signal from the conversation.\n"
        "- Do not invent facts.\n\n"
        'Return ONLY JSON: {"risk_level": "low|medium|high", "reason": "..." }\n'
        "No extra keys. No markdown.\n\n"
        f"Conversation:\n{text[:6000]}"
    )
    data = _llm_json(prompt)
    if data:
        level = str(data.get("risk_level", "")).strip().lower()
        reason = str(data.get("reason", "")).strip()
        if level in _VALID_RISK_LEVELS:
            return {"risk_level": level, "reason": reason[:512]}

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
# 5. generate_summary — 2 concise lines
# ---------------------------------------------------------------------------

def generate_summary(text: str, extracted: dict[str, Any] | None = None) -> str:
    """Return a concise 2-3 sentence summary."""
    prompt = (
        "Summarize the conversation in 2-3 concise sentences.\n"
        "Transcript may contain ASR noise; infer meaning conservatively.\n\n"
        "Sentence 1: who is involved and what they need/issue.\n"
        "Sentence 2: current decision status, risk, and explicit next step.\n"
        "Sentence 3 (optional): buying context such as timeline, budget, or stakeholders.\n"
        "Use factual language only from the conversation.\n"
        "No headings, no bullets, no JSON.\n\n"
        f"Conversation:\n{text[:8000]}"
    )
    summary = _llm_text(prompt)
    if summary and len(summary.split()) >= 10:
        # Normalize common ASR-inflated price mentions in summaries for map-update calls.
        hint_budget = infer_budget_hint(text)
        if hint_budget:
            summary = re.sub(r"\$\s*([0-9]{1,3}(?:,[0-9]{3})+)", lambda m: f"${hint_budget}" if "," in m.group(1) else m.group(0), summary)
        # Keep summary compact and at most three sentences.
        parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+", summary) if p.strip()]
        if len(parts) >= 2:
            return " ".join(parts[:3])[:1024]
        return summary[:1024]

    # Deterministic fallback to avoid poor summaries when LLM is unavailable/rate-limited.
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

    s1_parts = []
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
    elif next_step:
        s2 = f"Next step is {next_step.lower().strip('.')}."
    elif "demo" in low and "next week" in low:
        s2 = "Next step is a detailed demo with the team early next week."
    elif timeline:
        s2 = f"Target timeline is {timeline.lower().strip('.')} with evaluation in progress."
    elif competitors:
        s2 = "Prospect is comparing alternatives and requires stronger differentiation."
    else:
        s2 = "Conversation captures pricing and support details with follow-up pending confirmation."
    s3 = ""
    if timeline:
        s3 = f"Expected implementation timeline is {timeline.lower().strip('.')}."
    elif pain_points:
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
    prompt = (
        "Extract CRM tags from the conversation.\n\n"
        "Allowed tags only:\n"
        "urgent, enterprise, small-business, follow-up, demo-request, pricing, technical,\n"
        "renewal, upsell, new-lead, escalation, decision-maker, budget-approved, competitor-mentioned.\n\n"
        "Rules:\n"
        "- Include all applicable tags directly supported by explicit evidence.\n"
        "- No synonyms or custom tags.\n"
        "- Deduplicate tags.\n"
        "- Max 8 tags.\n\n"
        'Return ONLY JSON: {"tags": ["tag1", "tag2"]}\n'
        "No extra keys.\n\n"
        f"Conversation:\n{text[:6000]}"
    )
    data = _llm_json(prompt)
    if data:
        tags = data.get("tags", [])
        if isinstance(tags, list):
            cleaned = [str(t).strip().lower() for t in tags if str(t).strip()][:8]
            if cleaned:
                return cleaned

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
        "Write a professional follow-up email body in 3-5 sentences.\n"
        "Use only the provided CRM context. Do not invent missing details.\n"
        "Tone: helpful, concise, business-friendly.\n"
        "Include one clear CTA in the final sentence.\n"
        "Do not include subject line, greeting, signature, bullets, or placeholders.\n"
        "Return only email body text.\n\n"
        f"CRM context:\n{context_str}"
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
