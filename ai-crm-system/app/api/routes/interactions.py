"""Unified interaction timeline (FRD 2.4 / DRD 3.1)."""

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.db.models import CrmRecord
from app.utils.budget import parse_budget_to_int

router = APIRouter(prefix="/interactions", tags=["interactions"])


class TimelineItem(BaseModel):
    """Single interaction for unified history."""

    id: int
    created_at: datetime | None = None
    source_type: str = "call"
    external_interaction_id: str | None = None
    participants: list[str] = Field(default_factory=list)
    content_excerpt: str = Field("", description="Short preview of transcript body")
    budget_parsed: int = 0
    intent: str = ""
    account_id: int | None = None
    contact_id: int | None = None
    deal_id: int | None = None


class TimelineResponse(BaseModel):
    items: list[TimelineItem]
    total_returned: int


@router.get("/timeline", response_model=TimelineResponse)
def get_interaction_timeline(
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=500),
    source_type: str | None = Query(
        None,
        description="Filter by channel: call, email, meeting, sms, crm_update",
    ),
) -> TimelineResponse:
    """Chronological list of captured interactions (newest first)."""
    stmt = select(CrmRecord).order_by(CrmRecord.created_at.desc()).limit(limit)
    if source_type:
        stmt = stmt.where(CrmRecord.source_type == source_type[:64])
    rows = db.scalars(stmt).all()
    items: list[TimelineItem] = []
    for row in rows:
        raw = row.content or ""
        excerpt = raw.strip()[:280] + ("…" if len(raw.strip()) > 280 else "")
        plist = row.participants if isinstance(row.participants, list) else []
        items.append(
            TimelineItem(
                id=row.id,
                created_at=row.created_at,
                source_type=row.source_type or "call",
                external_interaction_id=row.external_interaction_id,
                participants=[str(p) for p in plist if p is not None][:32],
                content_excerpt=excerpt,
                budget_parsed=parse_budget_to_int(row.budget),
                intent=row.intent or "",
                account_id=row.account_id,
                contact_id=row.contact_id,
                deal_id=row.deal_id,
            )
        )
    return TimelineResponse(items=items, total_returned=len(items))
