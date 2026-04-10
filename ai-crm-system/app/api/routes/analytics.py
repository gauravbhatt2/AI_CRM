"""Analytics endpoints backed by CRM data."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.db.models import CrmRecord
from app.utils.budget import parse_budget_to_int

router = APIRouter(prefix="/analytics", tags=["analytics"])


class RevenueRecordItem(BaseModel):
    id: int
    budget: int
    intent: str
    timeline: str


class RevenueResponse(BaseModel):
    total_records: int = Field(..., description="Count of CRM records")
    total_budget: int = Field(..., description="Sum of parsed budget values")
    records: list[RevenueRecordItem]


@router.get("/revenue", response_model=RevenueResponse)
def get_revenue_data(db: Session = Depends(get_db)) -> RevenueResponse:
    """Aggregate budget-related fields from all `crm_records` rows."""
    rows = db.scalars(select(CrmRecord).order_by(CrmRecord.id)).all()

    items: list[RevenueRecordItem] = []
    total_budget = 0

    for row in rows:
        b = parse_budget_to_int(row.budget)
        total_budget += b
        items.append(
            RevenueRecordItem(
                id=row.id,
                budget=b,
                intent=row.intent or "",
                timeline=row.timeline or "",
            )
        )

    return RevenueResponse(
        total_records=len(rows),
        total_budget=total_budget,
        records=items,
    )
