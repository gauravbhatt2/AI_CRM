"""
Follow-up drafts — professional email (hybrid: template if LLM unavailable) and short WhatsApp.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from app.agents._groq_text import groq_text_or_none
from app.services.ai_intelligence import generate_email_draft

logger = logging.getLogger(__name__)

_MAX_EMAIL_WORDS = 120


def _truncate_words(text: str, max_words: int) -> str:
    words = text.replace("\n", " ").split()
    if len(words) <= max_words:
        return " ".join(words).strip()
    return " ".join(words[:max_words]).strip()


def _record_context_snippet(record: dict[str, Any]) -> str:
    keys = (
        "mentioned_company",
        "product",
        "pain_points",
        "next_step",
        "summary",
        "intent",
        "timeline",
        "next_action",
    )
    parts: list[str] = []
    for k in keys:
        v = record.get(k)
        if v is None:
            continue
        s = str(v).strip()
        if not s or s.lower() in ("n/a", "na", "none"):
            continue
        parts.append(f"{k}: {s[:500]}")
    return "\n".join(parts)[:6000]


def generate_followup_email(record: dict[str, Any]) -> str:
    ctx = _record_context_snippet(record)
    prompt = (
        "Write a professional follow-up email to the prospect.\n"
        "Requirements: friendly tone; include a short recap, their pain points, and clear next steps.\n"
        f"Max {_MAX_EMAIL_WORDS} words. No subject line. Body only.\n\n"
        f"CRM context:\n{ctx}\n\nEmail:"
    )
    out = groq_text_or_none(prompt, max_tokens=500, temperature=0.35)
    if out:
        body = re.sub(r"^(subject:.*\n)+", "", out, flags=re.I | re.M).strip()
        return _truncate_words(body, _MAX_EMAIL_WORDS)
    return _truncate_words(generate_email_draft(record), _MAX_EMAIL_WORDS)


def generate_whatsapp_message(record: dict[str, Any]) -> str:
    ctx = _record_context_snippet(record)
    prompt = (
        "Write a WhatsApp message to the prospect.\n"
        "2-3 short lines, casual tone, actionable. No emojis unless natural.\n\n"
        f"CRM context:\n{ctx}\n\nMessage:"
    )
    out = groq_text_or_none(prompt, max_tokens=120, temperature=0.4)
    if out:
        lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
        text = "\n".join(lines[:4]).strip()
        if text:
            return text
    company = str(record.get("mentioned_company") or "").strip() or "there"
    product = str(record.get("product") or "").strip() or "our chat"
    step = str(record.get("next_step") or "").strip()
    if step and step.lower() not in ("n/a", "na", ""):
        return f"Hi {company.split()[0] if company else 'there'} — quick ping on {product}.\n{step}\nLet me know what works for you."
    return f"Hi — following up on {product}.\nCan we find 15m this week to align on next steps?\nThanks!"
