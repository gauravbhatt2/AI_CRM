from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
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


def _structured_for_api(raw: dict | None) -> dict | None:
    if isinstance(raw, dict):
        return raw
    return None


class CrmRecordOut(BaseModel):
    """Single CRM record for API responses."""

    id: int
    content: str
    budget: int = Field(..., description="Parsed numeric budget")
    intent: str
    product: str
    product_version: str = ""
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
    structured_transcript: dict | None = None
    # AI Intelligence Layer
    interaction_type: str = ""
    deal_score: int = 0
    risk_level: str = ""
    risk_reason: str = ""
    summary: str = ""
    tags: list[str] = Field(default_factory=list)
    next_action: str = ""
    pain_points: str = ""
    next_step: str = ""
    urgency_reason: str = ""
    stakeholders: list[str] = Field(default_factory=list)
    mentioned_company: str = ""
    procurement_stage: str = ""
    use_case: str = ""
    decision_criteria: str = ""
    budget_owner: str = ""
    implementation_scope: str = ""


class CrmRecordPatchIn(BaseModel):
    budget: str | None = None
    intent: str | None = None
    product: str | None = None
    product_version: str | None = None
    timeline: str | None = None
    industry: str | None = None
    competitors: list[str] | None = None
    pain_points: str | None = None
    next_step: str | None = None
    urgency_reason: str | None = None
    stakeholders: list[str] | None = None
    mentioned_company: str | None = None
    procurement_stage: str | None = None
    use_case: str | None = None
    decision_criteria: str | None = None
    budget_owner: str | None = None
    implementation_scope: str | None = None
    summary: str | None = None
    next_action: str | None = None
    risk_level: str | None = None
    risk_reason: str | None = None
    interaction_type: str | None = None
    deal_score: int | None = None
    tags: list[str] | None = None
    content: str | None = None
    structured_transcript: dict | None = None
    custom_fields: dict[str, str] | None = None


def _format_content_from_structured(st: dict | None, fallback: str) -> str:
    if not isinstance(st, dict):
        return fallback
    segs = st.get("segments")
    if not isinstance(segs, list):
        return fallback

    def _fmt_ts(sec: object) -> str:
        try:
            s = max(0, int(float(sec)))
        except (TypeError, ValueError):
            s = 0
        m, r = divmod(s, 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h:02d}:{m:02d}:{r:02d}"
        return f"{m:02d}:{r:02d}"

    lines: list[str] = []
    for seg in segs:
        if not isinstance(seg, dict):
            continue
        txt = str(seg.get("text") or "").strip()
        if not txt:
            continue
        sp = str(seg.get("speaker") or "").strip()
        line = f"[{_fmt_ts(seg.get('start'))}-{_fmt_ts(seg.get('end'))}] "
        line += f"{sp}: {txt}" if sp else txt
        lines.append(line)
    return "\n".join(lines) if lines else fallback


def _to_crm_record_out(row: CrmRecord) -> CrmRecordOut:
    return CrmRecordOut(
        id=row.id,
        content=row.content,
        budget=parse_budget_to_int(row.budget),
        intent=row.intent or "",
        product=row.product or "",
        product_version=getattr(row, "product_version", "") or "",
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
        structured_transcript=_structured_for_api(getattr(row, "structured_transcript", None)),
        interaction_type=getattr(row, "interaction_type", "") or "",
        deal_score=getattr(row, "deal_score", 0) or 0,
        risk_level=getattr(row, "risk_level", "") or "",
        risk_reason=getattr(row, "risk_reason", "") or "",
        summary=getattr(row, "summary", "") or "",
        tags=_competitors_for_api(getattr(row, "tags", None)),
        next_action=getattr(row, "next_action", "") or "",
        pain_points=str(getattr(row, "pain_points", "") or ""),
        next_step=getattr(row, "next_step", "") or "",
        urgency_reason=getattr(row, "urgency_reason", "") or "",
        stakeholders=_participants_for_api(getattr(row, "stakeholders", None)),
        mentioned_company=getattr(row, "mentioned_company", "") or "",
        procurement_stage=getattr(row, "procurement_stage", "") or "",
        use_case=getattr(row, "use_case", "") or "",
        decision_criteria=getattr(row, "decision_criteria", "") or "",
        budget_owner=getattr(row, "budget_owner", "") or "",
        implementation_scope=getattr(row, "implementation_scope", "") or "",
    )


@router.get("/records", response_model=list[CrmRecordOut])
def list_crm_records(db: Session = Depends(get_db)) -> list[CrmRecordOut]:
    """Return all rows from `crm_records` with budget as integer."""
    rows = db.scalars(select(CrmRecord).order_by(CrmRecord.id)).all()
    return [_to_crm_record_out(row) for row in rows]


@router.get("/records/{record_id}", response_model=CrmRecordOut)
def get_crm_record(record_id: int, db: Session = Depends(get_db)) -> CrmRecordOut:
    row = db.get(CrmRecord, record_id)
    if row is None:
        raise HTTPException(status_code=404, detail="CRM record not found")
    return _to_crm_record_out(row)


@router.patch("/records/{record_id}", response_model=CrmRecordOut)
def patch_crm_record(
    record_id: int,
    body: CrmRecordPatchIn,
    db: Session = Depends(get_db),
) -> CrmRecordOut:
    row = db.get(CrmRecord, record_id)
    if row is None:
        raise HTTPException(status_code=404, detail="CRM record not found")

    for key, value in body.model_dump(exclude_unset=True).items():
        if key == "structured_transcript":
            row.structured_transcript = value
            row.content = _format_content_from_structured(value, row.content or "")
            continue
        if key == "custom_fields":
            row.custom_fields = _custom_fields_for_api(value)
            continue
        if key in ("competitors", "stakeholders", "tags"):
            row_val = [str(x).strip() for x in (value or []) if str(x).strip()]
            setattr(row, key, row_val)
            continue
        if key == "deal_score":
            setattr(row, key, int(value or 0))
            continue
        if key == "budget":
            row.budget = str(value or "").strip()
            continue
        setattr(row, key, "" if value is None else str(value))

    db.commit()
    db.refresh(row)
    return _to_crm_record_out(row)


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
