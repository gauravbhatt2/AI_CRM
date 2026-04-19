"""Thin alias for CRM record listing (`GET /api/v1/records`)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.routes.crm import CrmRecordOut, list_crm_records

router = APIRouter(prefix="/records", tags=["records"])


@router.get("", response_model=list[CrmRecordOut])
def get_all_records(db: Session = Depends(get_db)) -> list[CrmRecordOut]:
    """Same payload as ``GET /api/v1/crm/records`` (intent, risk, score, next_action, …)."""
    return list_crm_records(db)
