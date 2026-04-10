"""Analytics endpoints backed by CRM data."""

from collections import Counter

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


class InsightsResponse(BaseModel):
    """FRD 2.5 — revenue / interaction intelligence summary."""

    total_interactions: int = Field(..., description="Count of CRM records")
    total_budget_sum: int = Field(..., description="Sum of parsed budgets")
    avg_budget: float = Field(..., description="Average parsed budget (0 if none)")
    by_source_type: dict[str, int] = Field(
        default_factory=dict,
        description="Record counts per channel",
    )
    intent_keywords_high: int = Field(
        0,
        description="Records whose intent text mentions high / strong buying signals",
    )
    intent_keywords_low: int = Field(
        0,
        description="Records whose intent text mentions low / exploratory signals",
    )


@router.get("/insights", response_model=InsightsResponse)
def get_revenue_insights(db: Session = Depends(get_db)) -> InsightsResponse:
    """Aggregate deal-relevant signals for dashboards (FRD 2.5)."""
    rows = db.scalars(select(CrmRecord)).all()
    n = len(rows)
    total_b = 0
    by_src: Counter[str] = Counter()
    hi = 0
    lo = 0
    for row in rows:
        b = parse_budget_to_int(row.budget)
        total_b += b
        by_src[row.source_type or "unknown"] += 1
        it = (row.intent or "").lower()
        if any(x in it for x in ("high", "strong", "ready", "urgent")):
            hi += 1
        if any(x in it for x in ("low", "explor", "maybe", "just looking")):
            lo += 1
    avg = float(total_b) / n if n else 0.0
    return InsightsResponse(
        total_interactions=n,
        total_budget_sum=total_b,
        avg_budget=round(avg, 2),
        by_source_type=dict(by_src),
        intent_keywords_high=hi,
        intent_keywords_low=lo,
    )
