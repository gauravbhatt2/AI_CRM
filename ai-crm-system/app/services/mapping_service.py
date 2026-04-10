"""
Contextual CRM mapping: derive Account, Contact, and Deal from transcript + extraction.

Primary path: Gemini entity resolution against recent CRM rows. Fallback: rule-based heuristics.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Account, Contact, Deal
from app.services.gemini_mapping import llm_suggest_crm_links

logger = logging.getLogger(__name__)

# Words to ignore when treating capitalized tokens as person/company names
_SKIP_CAPITALIZED: frozenset[str] = frozenset(
    {
        "Spoke",
        "Talked",
        "Met",
        "With",
        "From",
        "The",
        "A",
        "An",
        "We",
        "They",
        "This",
        "That",
        "Call",
        "Meeting",
        "Regarding",
        "About",
        "Budget",
        "Timeline",
        "Intent",
        "Customer",
        "Client",
        "Team",
        "Sales",
        "Hi",
        "Hello",
        "Dear",
    }
)

DEFAULT_ACCOUNT_NAME = "Unknown Account"


def _normalize_label(s: str) -> str:
    return " ".join(s.split()).strip()


def _extract_company_from_transcript(transcript: str) -> str | None:
    """Prefer `from <Company>`; else last plausible Title-Case phrase."""
    t = transcript.strip()
    m = re.search(
        r"\bfrom\s+([A-Za-z0-9][A-Za-z0-9\s&.,'-]+?)(?=\s*[,.;]|\s+budget|\s+timeline|\s+about|\s*$)",
        t,
        flags=re.IGNORECASE,
    )
    if m:
        return _normalize_label(m.group(1))
    phrases = re.findall(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b", t)
    for phrase in reversed(phrases):
        if phrase in _SKIP_CAPITALIZED:
            continue
        if len(phrase) < 2:
            continue
        return phrase
    return None


def _extract_contact_from_transcript(transcript: str, company: str | None) -> str | None:
    """Prefer `with <Name>`; else first capitalized word that is not the company token."""
    t = transcript.strip()
    m = re.search(r"\bwith\s+([A-Z][a-z]+)\b", t)
    if m:
        return m.group(1)
    m2 = re.search(
        r"\b(?:spoke|talked|met)\s+(?:with\s+)?([A-Z][a-z]+)\b",
        t,
        flags=re.IGNORECASE,
    )
    if m2:
        return m2.group(1)
    company_lower = company.lower() if company else ""
    for word in re.findall(r"\b[A-Z][a-z]+\b", t):
        if word in _SKIP_CAPITALIZED:
            continue
        if company_lower and word.lower() in company_lower:
            continue
        return word
    return None


def _get_or_create_account(db: Session, name: str) -> Account:
    key = name.strip()
    if not key:
        key = DEFAULT_ACCOUNT_NAME
    existing = db.scalars(
        select(Account).where(func.lower(Account.name) == func.lower(key))
    ).first()
    if existing:
        return existing
    row = Account(name=key)
    db.add(row)
    db.flush()
    return row


def _get_or_create_contact(db: Session, *, account_id: int, name: str) -> Contact:
    key = name.strip()
    if not key:
        key = "Unknown Contact"
    existing = db.scalars(
        select(Contact).where(
            Contact.account_id == account_id,
            func.lower(Contact.name) == func.lower(key),
        )
    ).first()
    if existing:
        return existing
    row = Contact(account_id=account_id, name=key)
    db.add(row)
    db.flush()
    return row


def _create_deal(db: Session, *, account_id: int, value: str | None) -> Deal:
    row = Deal(account_id=account_id, value=value if value else None)
    db.add(row)
    db.flush()
    return row


def _budget_from_extracted(extracted_data: dict[str, Any]) -> str:
    if not isinstance(extracted_data, dict):
        return ""
    b = extracted_data.get("budget")
    if b is None:
        return ""
    return str(b).strip()


def _apply_llm_suggestion(
    db_session: Session,
    suggestion: dict[str, Any],
    transcript: str,
    extracted_data: dict[str, Any],
) -> dict[str, int | None] | None:
    ma = suggestion.get("match_account_id")
    mc = suggestion.get("match_contact_id")
    rc = str(suggestion.get("resolved_company") or "").strip()
    rp = str(suggestion.get("resolved_contact_person") or "").strip()

    account: Account | None = None
    if isinstance(ma, int):
        account = db_session.get(Account, ma)
    if account is None and rc:
        account = _get_or_create_account(db_session, rc)
    if account is None:
        return None

    contact: Contact | None = None
    if isinstance(mc, int):
        c = db_session.get(Contact, mc)
        if c and c.account_id == account.id:
            contact = c
    if contact is None and rp:
        contact = _get_or_create_contact(
            db_session,
            account_id=account.id,
            name=rp,
        )
    if contact is None:
        person = _extract_contact_from_transcript(transcript, account.name)
        if person:
            contact = _get_or_create_contact(
                db_session,
                account_id=account.id,
                name=person,
            )

    budget_hint = _budget_from_extracted(extracted_data)
    deal = _create_deal(
        db_session,
        account_id=account.id,
        value=budget_hint or None,
    )

    return {
        "account_id": account.id,
        "contact_id": contact.id if contact else None,
        "deal_id": deal.id,
    }


def map_entities_to_crm_rules(
    transcript: str,
    extracted_data: dict[str, Any],
    db_session: Session,
) -> dict[str, int | None]:
    """
    Map transcript + extracted fields to Account, Contact, and Deal rows using heuristics only.

    Does not commit the session; caller should persist `CrmRecord` and commit.
    """
    try:
        company = _extract_company_from_transcript(transcript)
        if not company:
            company = DEFAULT_ACCOUNT_NAME

        person = _extract_contact_from_transcript(transcript, company)

        account = _get_or_create_account(db_session, company)

        contact: Contact | None = None
        if person:
            contact = _get_or_create_contact(
                db_session,
                account_id=account.id,
                name=person,
            )

        budget_hint = _budget_from_extracted(extracted_data)

        deal = _create_deal(
            db_session,
            account_id=account.id,
            value=budget_hint or None,
        )

        return {
            "account_id": account.id,
            "contact_id": contact.id if contact else None,
            "deal_id": deal.id,
        }
    except Exception:
        logger.exception(
            "map_entities_to_crm_rules failed; persisting crm_record without CRM links",
        )
        try:
            db_session.rollback()
        except Exception:
            logger.exception("Session rollback after mapping failure failed")
        return {
            "account_id": None,
            "contact_id": None,
            "deal_id": None,
        }


def map_entities_to_crm(
    transcript: str,
    extracted_data: dict[str, Any],
    db_session: Session,
) -> tuple[dict[str, int | None], str]:
    """
    Try Gemini-assisted resolution against recent CRM rows; fall back to rule-based mapping.

    Returns (ids, method) where method is 'llm', 'rules', or 'rules_fallback'.
    """
    suggestion = llm_suggest_crm_links(db_session, transcript, extracted_data)
    if isinstance(suggestion, dict) and suggestion:
        try:
            mapped = _apply_llm_suggestion(
                db_session,
                suggestion,
                transcript,
                extracted_data,
            )
            if mapped and mapped.get("account_id") is not None:
                return mapped, "llm"
        except Exception:
            logger.exception("LLM CRM mapping application failed; using rules")

    mapped = map_entities_to_crm_rules(transcript, extracted_data, db_session)
    method = "rules_fallback" if suggestion is not None else "rules"
    return mapped, method


class MappingService:
    """Legacy helper for `/crm/map` — full mapping runs on ingest via `map_entities_to_crm`."""

    def map_to_crm(self, extracted: dict[str, Any]) -> dict[str, Any]:
        """Lightweight shape for the standalone map endpoint (no transcript / DB)."""
        _ = extracted
        return {
            "mapped": False,
            "detail": "Use POST /ingest/transcript for transcript-based Account, Contact, and Deal mapping.",
        }
