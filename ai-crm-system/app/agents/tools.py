"""
Agent helpers: DB access, HubSpot update hook, email stub.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import CrmRecord
from app.integrations.gmail_service import send_email as gmail_send_email

logger = logging.getLogger(__name__)


def crm_row_to_agent_record(row: CrmRecord) -> dict[str, Any]:
    """Flatten an ORM row into the dict shape used by agents."""
    cf = row.custom_fields if isinstance(row.custom_fields, dict) else {}
    return {
        "id": row.id,
        "content": row.content or "",
        "budget": row.budget or "",
        "intent": row.intent or "",
        "competitors": list(row.competitors or []),
        "product": row.product or "",
        "product_version": getattr(row, "product_version", "") or "",
        "timeline": row.timeline or "",
        "industry": row.industry or "",
        "custom_fields": dict(cf),
        "source_type": row.source_type or "",
        "interaction_type": getattr(row, "interaction_type", "") or "",
        "deal_score": int(getattr(row, "deal_score", 0) or 0),
        "risk_level": getattr(row, "risk_level", "") or "",
        "risk_reason": getattr(row, "risk_reason", "") or "",
        "summary": getattr(row, "summary", "") or "",
        "tags": list(getattr(row, "tags", None) or []),
        "next_action": getattr(row, "next_action", "") or "",
        "pain_points": getattr(row, "pain_points", "") or "",
        "next_step": getattr(row, "next_step", "") or "",
        "urgency_reason": getattr(row, "urgency_reason", "") or "",
        "stakeholders": list(getattr(row, "stakeholders", None) or []),
        "mentioned_company": getattr(row, "mentioned_company", "") or "",
        "procurement_stage": getattr(row, "procurement_stage", "") or "",
        "use_case": getattr(row, "use_case", "") or "",
        "decision_criteria": getattr(row, "decision_criteria", "") or "",
        "budget_owner": getattr(row, "budget_owner", "") or "",
        "implementation_scope": getattr(row, "implementation_scope", "") or "",
        "followup_email": getattr(row, "followup_email", "") or "",
        "source_metadata": row.source_metadata if isinstance(row.source_metadata, dict) else {},
    }


def get_crm_record(db: Session, record_id: int) -> dict[str, Any] | None:
    row = db.get(CrmRecord, record_id)
    if row is None:
        return None
    return crm_row_to_agent_record(row)


def get_transcript(db: Session, record_id: int) -> str | None:
    row = db.get(CrmRecord, record_id)
    if row is None:
        return None
    return row.content or ""


def update_hubspot_deal(record_id: int, fields: dict[str, Any]) -> dict[str, Any]:
    """
    Stub for updating an existing HubSpot deal.

    Production path: resolve hubspot_deal_id from `source_metadata` after a push,
    then PATCH crm/v3/objects/deals/{id}. Not invoked automatically.
    """
    _ = record_id
    token = (settings.hubspot_api_key or "").strip()
    if not token:
        logger.info("update_hubspot_deal stub: no HUBSPOT_API_KEY; fields=%s", list(fields.keys()))
        return {"ok": False, "detail": "HubSpot not configured (stub)"}
    logger.info("update_hubspot_deal stub: would PATCH deal properties keys=%s", list(fields.keys()))
    return {"ok": True, "detail": "stub_no_op", "record_id": record_id, "accepted_keys": list(fields.keys())}


def send_email(to: str, subject: str, body: str) -> dict[str, Any]:
    """Delegates to integrations Gmail layer (mock by default)."""
    return gmail_send_email(to, subject, body)
