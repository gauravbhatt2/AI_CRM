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


class AIIntelligenceItem(BaseModel):
    id: int
    interaction_type: str = ""
    deal_score: int = 0
    risk_level: str = ""
    risk_reason: str = ""
    summary: str = ""
    tags: list[str] = Field(default_factory=list)
    next_action: str = ""
    intent: str = ""
    budget: int = 0
    product: str = ""


class AIIntelligenceResponse(BaseModel):
    total_records: int
    intent_distribution: dict[str, int] = Field(
        default_factory=dict,
        description="Count of records per interaction_type",
    )
    risk_distribution: dict[str, int] = Field(
        default_factory=dict,
        description="Count of records per risk_level",
    )
    avg_deal_score: float = 0.0
    records: list[AIIntelligenceItem]


@router.get("/ai-intelligence", response_model=AIIntelligenceResponse)
def get_ai_intelligence(db: Session = Depends(get_db)) -> AIIntelligenceResponse:
    """AI Intelligence aggregation: interaction types, risk levels, deal scores."""
    rows = db.scalars(select(CrmRecord).order_by(CrmRecord.id)).all()

    items: list[AIIntelligenceItem] = []
    intent_dist: Counter[str] = Counter()
    risk_dist: Counter[str] = Counter()
    score_sum = 0

    for row in rows:
        itype = getattr(row, "interaction_type", "") or ""
        dscore = getattr(row, "deal_score", 0) or 0
        rlevel = getattr(row, "risk_level", "") or ""
        rreason = getattr(row, "risk_reason", "") or ""
        summary = getattr(row, "summary", "") or ""
        tags_raw = getattr(row, "tags", None)
        tags_list = [str(t) for t in tags_raw if t] if isinstance(tags_raw, list) else []
        naction = getattr(row, "next_action", "") or ""

        if itype:
            intent_dist[itype] += 1
        if rlevel:
            risk_dist[rlevel] += 1
        score_sum += dscore

        items.append(
            AIIntelligenceItem(
                id=row.id,
                interaction_type=itype,
                deal_score=dscore,
                risk_level=rlevel,
                risk_reason=rreason,
                summary=summary,
                tags=tags_list,
                next_action=naction,
                intent=row.intent or "",
                budget=parse_budget_to_int(row.budget),
                product=row.product or "",
            )
        )

    n = len(rows)
    return AIIntelligenceResponse(
        total_records=n,
        intent_distribution=dict(intent_dist),
        risk_distribution=dict(risk_dist),
        avg_deal_score=round(score_sum / n, 1) if n else 0.0,
        records=items,
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
