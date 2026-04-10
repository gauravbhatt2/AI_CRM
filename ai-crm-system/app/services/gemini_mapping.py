"""
Gemini-assisted resolution of transcript + extraction to existing CRM rows (entity resolution).
"""

from __future__ import annotations

import json
import logging
import re
import warnings
from typing import Any

with warnings.catch_warnings():
    warnings.simplefilter("ignore", category=FutureWarning)
    import google.generativeai as genai

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Account, Contact
from app.services.gemini_extraction import GEMINI_SAFETY_SETTINGS, extract_text_from_gemini_response

logger = logging.getLogger(__name__)

_CONFIGURED = False


def _ensure_configured() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    key = settings.gemini_api_key
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not set")
    genai.configure(api_key=key)
    _CONFIGURED = True


def _resolve_model_name(name: str) -> str:
    aliases = {
        "gemini-1.5-flash": "gemini-2.5-flash",
        "gemini-1.5-flash-8b": "gemini-2.5-flash",
        "gemini-1.5-pro": "gemini-2.5-pro",
    }
    return aliases.get(name.strip().lower(), name.strip())


def _strip_markdown_fences(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```\s*$", "", text)
    return text.strip()


def _recent_accounts(db: Session, limit: int = 48) -> list[dict[str, Any]]:
    rows = db.scalars(select(Account).order_by(Account.id.desc()).limit(limit)).all()
    return [{"id": r.id, "name": r.name} for r in rows]


def _recent_contacts(db: Session, limit: int = 64) -> list[dict[str, Any]]:
    rows = db.scalars(select(Contact).order_by(Contact.id.desc()).limit(limit)).all()
    return [{"id": r.id, "name": r.name, "account_id": r.account_id} for r in rows]


def llm_suggest_crm_links(
    db: Session,
    transcript: str,
    extracted: dict[str, Any],
) -> dict[str, Any] | None:
    """
    Ask Gemini to pick existing account/contact ids or suggest canonical company and person names.

    Returns None on any failure (caller falls back to rules).
    """
    try:
        _ensure_configured()
    except RuntimeError:
        return None

    raw_name = (settings.gemini_model or "").strip()
    if not raw_name:
        return None

    accounts = _recent_accounts(db)
    contacts = _recent_contacts(db)
    ext_json = json.dumps(extracted, ensure_ascii=False)[:8000]

    prompt = f"""You map a sales interaction to CRM records using entity resolution.

Given:
1) Conversation text
2) Extracted structured fields (JSON)
3) Recent accounts (id, name) — prefer linking when clearly the same company
4) Recent contacts (id, name, account_id) — prefer linking when clearly the same person

Return ONLY valid JSON:
{{
  "match_account_id": <number or null>,
  "match_contact_id": <number or null>,
  "resolved_company": "<best company name to use if creating or matching>",
  "resolved_contact_person": "<best person name if known, else empty string>"
}}

Rules:
- Only use match_account_id / match_contact_id if they clearly fit the conversation; else null.
- If unsure, set ids to null and fill resolved_company / resolved_contact_person from the text.
- resolved_company should not be empty unless truly unknown.

Extracted fields:
{ext_json}

Recent accounts:
{json.dumps(accounts, ensure_ascii=False)}

Recent contacts:
{json.dumps(contacts, ensure_ascii=False)}

Conversation:
{transcript.strip()[:24000]}
"""

    model_name = _resolve_model_name(raw_name)
    try:
        model = genai.GenerativeModel(
            model_name,
            safety_settings=GEMINI_SAFETY_SETTINGS,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
            ),
        )
        response = model.generate_content(prompt)
        raw = extract_text_from_gemini_response(response)
    except Exception:
        logger.exception("Gemini CRM mapping request failed")
        return None

    if not raw:
        return None
    try:
        parsed = json.loads(_strip_markdown_fences(raw))
    except (json.JSONDecodeError, TypeError, ValueError):
        logger.warning("Gemini CRM mapping JSON parse failed")
        return None
    if not isinstance(parsed, dict):
        return None
    return parsed
