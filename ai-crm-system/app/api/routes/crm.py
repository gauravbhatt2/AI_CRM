from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.db.models import CrmRecord
from app.models.crm import CRMMapRequest, CRMMapResponse
from app.services.mapping_service import MappingService
from app.utils.budget import parse_budget_to_int

router = APIRouter(prefix="/crm", tags=["crm"])

_mapping = MappingService()


class CrmRecordOut(BaseModel):
    """Single CRM record for API responses."""

    id: int
    content: str
    budget: int = Field(..., description="Parsed numeric budget")
    intent: str
    product: str
    timeline: str
    industry: str = ""
    custom_fields: dict[str, str] = Field(default_factory=dict)
    source_type: str = "call"
    mapping_method: str = "rules"
    account_id: int | None = None
    contact_id: int | None = None
    deal_id: int | None = None


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
            custom_fields=dict(row.custom_fields or {}),
            source_type=row.source_type or "call",
            mapping_method=row.mapping_method or "rules",
            account_id=row.account_id,
            contact_id=row.contact_id,
            deal_id=row.deal_id,
        )
        for row in rows
    ]


@router.post("/map", response_model=CRMMapResponse)
async def map_to_crm(body: CRMMapRequest) -> CRMMapResponse:
    """Placeholder: apply extracted payload to CRM entities."""
    payload = body.payload if isinstance(body.payload, dict) else {}
    result = _mapping.map_to_crm(payload)
    return CRMMapResponse(
        mapped=bool(result.get("mapped")),
        detail=str(result.get("detail", "Use POST /ingest/transcript for full mapping.")),
    )
