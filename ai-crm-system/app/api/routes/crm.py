from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.db.models import CrmRecord
from app.models.crm import CRMMapRequest, CRMMapResponse
from app.services.mapping_service import MappingService
from app.utils.budget import parse_budget_to_int

router = APIRouter(prefix="/crm", tags=["crm"])

_mapping = MappingService()


def _custom_fields_for_api(raw: dict | None) -> dict[str, str]:
    """JSONB may contain non-strings; API contract is dict[str, str]."""
    out: dict[str, str] = {}
    if not raw or not isinstance(raw, dict):
        return out
    for k, v in raw.items():
        ks = str(k).strip()
        if not ks:
            continue
        if v is None:
            continue
        out[ks] = str(v)
    return out


def _competitors_for_api(raw: list | None) -> list[str]:
    if not raw or not isinstance(raw, list):
        return []
    return [str(c) for c in raw if c is not None and str(c).strip() != ""]


def _participants_for_api(raw: list | None) -> list[str]:
    if not raw or not isinstance(raw, list):
        return []
    return [str(p).strip() for p in raw if p is not None and str(p).strip() != ""]


class CrmRecordOut(BaseModel):
    """Single CRM record for API responses."""

    id: int
    content: str
    budget: int = Field(..., description="Parsed numeric budget")
    intent: str
    product: str
    timeline: str
    industry: str = ""
    competitors: list[str] = Field(default_factory=list)
    custom_fields: dict[str, str] = Field(default_factory=dict)
    source_type: str = "call"
    mapping_method: str = "rules"
    account_id: int | None = None
    contact_id: int | None = None
    deal_id: int | None = None
    created_at: datetime | None = None
    external_interaction_id: str | None = None
    participants: list[str] = Field(default_factory=list)


@router.get("/records", response_model=list[CrmRecordOut])
def list_crm_records(db: Session = Depends(get_db)) -> list[CrmRecordOut]:
    """Return all rows from `crm_records` with budget as integer."""
    rows = db.scalars(select(CrmRecord).order_by(CrmRecord.id)).all()
    return [
        CrmRecordOut(
            id=row.id,
            content=row.content,
            budget=parse_budget_to_int(row.budget),
            intent=row.intent or "",
            product=row.product or "",
            timeline=row.timeline or "",
            industry=row.industry or "",
            competitors=_competitors_for_api(row.competitors),
            custom_fields=_custom_fields_for_api(row.custom_fields),
            source_type=row.source_type or "call",
            mapping_method=row.mapping_method or "rules",
            account_id=row.account_id,
            contact_id=row.contact_id,
            deal_id=row.deal_id,
            created_at=row.created_at,
            external_interaction_id=row.external_interaction_id,
            participants=_participants_for_api(row.participants),
        )
        for row in rows
    ]


class DeleteRecordsResponse(BaseModel):
    deleted: int = Field(..., description="Number of rows removed from crm_records")


@router.delete("/records", response_model=DeleteRecordsResponse)
def delete_all_crm_records(db: Session = Depends(get_db)) -> DeleteRecordsResponse:
    """Remove every row from `crm_records` (destructive; use for local reset)."""
    result = db.execute(delete(CrmRecord))
    db.commit()
    return DeleteRecordsResponse(deleted=int(result.rowcount or 0))


@router.post("/map", response_model=CRMMapResponse)
async def map_to_crm(body: CRMMapRequest) -> CRMMapResponse:
    """Placeholder: apply extracted payload to CRM entities."""
    payload = body.payload if isinstance(body.payload, dict) else {}
    result = _mapping.map_to_crm(payload)
    return CRMMapResponse(
        mapped=bool(result.get("mapped")),
        detail=str(result.get("detail", "Use POST /ingest/transcript for full mapping.")),
    )
