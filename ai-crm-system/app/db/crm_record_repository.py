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
