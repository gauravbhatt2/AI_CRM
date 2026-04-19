"""Persistence helpers for `crm_records`."""

from sqlalchemy.orm import Session

from app.db.models import CrmRecord
from app.models.ingestion import ExtractedEntities, StructuredTranscript


def create_crm_record(
    db: Session,
    *,
    content: str,
    extracted: ExtractedEntities,
    account_id: int | None = None,
    contact_id: int | None = None,
    deal_id: int | None = None,
    source_type: str = "call",
    source_metadata: dict | None = None,
    structured_transcript: StructuredTranscript | dict | None = None,
    mapping_method: str = "rules",
    external_interaction_id: str | None = None,
    participants: list[str] | None = None,
    ai_intelligence: dict | None = None,
    followup_email: str | None = None,
) -> CrmRecord:
    """Insert a row from transcript text, structured extraction, and optional CRM links."""
    st: dict | None = None
    if structured_transcript is not None:
        if isinstance(structured_transcript, StructuredTranscript):
            st = structured_transcript.model_dump()
        elif isinstance(structured_transcript, dict):
            st = structured_transcript

    meta = source_metadata if isinstance(source_metadata, dict) else {}
    plist: list[str] = []
    if isinstance(participants, list):
        for p in participants:
            ps = str(p).strip()
            if ps and ps not in plist:
                plist.append(ps[:512])

    ai = ai_intelligence if isinstance(ai_intelligence, dict) else {}

    row = CrmRecord(
        content=content,
        budget=extracted.budget,
        intent=extracted.intent,
        competitors=list(extracted.competitors),
        product=extracted.product,
        timeline=extracted.timeline,
        industry=extracted.industry,
        custom_fields=dict(extracted.custom_fields),
        account_id=account_id,
        contact_id=contact_id,
        deal_id=deal_id,
        source_type=(source_type or "call")[:64],
        external_interaction_id=(external_interaction_id or None),
        participants=plist,
        source_metadata=meta,
        structured_transcript=st,
        mapping_method=(mapping_method or "rules")[:32],
        # AI Intelligence fields
        interaction_type=str(ai.get("interaction_type", ""))[:64],
        deal_score=int(ai.get("deal_score", 0)),
        risk_level=str(ai.get("risk_level", ""))[:32],
        risk_reason=str(ai.get("risk_reason", ""))[:2048],
        summary=str(ai.get("summary", ""))[:4096],
        tags=list(ai.get("tags", [])),
        next_action=str(ai.get("next_action", ""))[:2048],
        followup_email=str(followup_email or "")[:16000],
        # Extraction-enriched fields
        product_version=getattr(extracted, "product_version", "") or "",
        pain_points=str(getattr(extracted, "pain_points", "") or ""),
        next_step=getattr(extracted, "next_step", "") or "",
        urgency_reason=getattr(extracted, "urgency_reason", "") or "",
        stakeholders=list(getattr(extracted, "stakeholders", []) or []),
        mentioned_company=str(getattr(extracted, "mentioned_company", "") or ""),
        procurement_stage=str(getattr(extracted, "procurement_stage", "") or "")[:128],
        use_case=str(getattr(extracted, "use_case", "") or ""),
        decision_criteria=str(getattr(extracted, "decision_criteria", "") or ""),
        budget_owner=str(getattr(extracted, "budget_owner", "") or "")[:256],
        implementation_scope=str(getattr(extracted, "implementation_scope", "") or "")[:256],
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_crm_record_structured_transcript(
    db: Session,
    record_id: int,
    structured_transcript: StructuredTranscript | dict,
) -> None:
    """Update only `structured_transcript` (e.g. after optional speaker labeling)."""
    row = db.get(CrmRecord, record_id)
    if row is None:
        return
    if isinstance(structured_transcript, StructuredTranscript):
        row.structured_transcript = structured_transcript.model_dump()
    elif isinstance(structured_transcript, dict):
        row.structured_transcript = structured_transcript
    db.commit()


def update_crm_record_content(db: Session, record_id: int, content: str) -> None:
    """Update stored transcript text (e.g. after adding speaker prefixes for display)."""
    row = db.get(CrmRecord, record_id)
    if row is None:
        return
    row.content = content
    db.commit()
