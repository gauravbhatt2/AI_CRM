"""
Shared ingestion: Groq extraction → CRM mapping → persist crm_record.
"""

from __future__ import annotations

import asyncio

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.audit_repository import log_audit_event
from app.db.crm_record_repository import create_crm_record
from app.db.models import CrmRecord
from app.ingestion.receiver import TranscriptReceiver
from app.models.ingestion import (
    AudioIngestResponse,
    ExtractedEntities,
    StructuredTranscript,
    TranscriptIngestResponse,
)
from app.services.ai_intelligence import run_ai_intelligence
from app.services.extraction_service import extract_entities
from app.services.mapping_service import map_entities_to_crm


def _merge_participants(meta: dict, explicit: list[str] | None) -> list[str]:
    """DRD participants: union of explicit list and metadata.participants."""
    out: list[str] = []
    if explicit:
        for p in explicit:
            s = str(p).strip()
            if s and s not in out:
                out.append(s[:512])
    raw = meta.get("participants")
    if isinstance(raw, list):
        for p in raw:
            s = str(p).strip()
            if s and s not in out:
                out.append(s[:512])
    return out[:64]


async def run_transcript_pipeline(
    *,
    transcript: str,
    db: Session,
    receiver: TranscriptReceiver,
    metadata: dict | None = None,
    external_id: str | None = None,
    participants: list[str] | None = None,
    source_type: str = "call",
    structured_transcript: StructuredTranscript | None = None,
) -> TranscriptIngestResponse:
    """Run extraction, mapping, and DB insert for a transcript string."""
    ctx = receiver.accept_transcript(
        content=transcript,
        metadata=metadata,
        external_id=external_id,
    )
    meta = dict(metadata or {})
    if external_id:
        meta.setdefault("external_id", external_id)
    plist = _merge_participants(meta, participants)
    ext_key = (external_id or str(meta.get("external_id") or "")).strip()[:256] or None

    prior_same_external = 0
    if ext_key:
        prior_same_external = (
            db.scalar(
                select(func.count())
                .select_from(CrmRecord)
                .where(CrmRecord.external_interaction_id == ext_key),
            )
            or 0
        )

    extracted_raw = await asyncio.to_thread(extract_entities, transcript)
    extracted = ExtractedEntities.model_validate(extracted_raw)
    mapped, map_method = map_entities_to_crm(
        transcript,
        extracted.model_dump(),
        db,
        source_metadata=meta,
    )

    ai_intel = await asyncio.to_thread(
        run_ai_intelligence, transcript, extracted.model_dump()
    )

    record = create_crm_record(
        db,
        content=transcript,
        extracted=extracted,
        account_id=mapped.get("account_id"),
        contact_id=mapped.get("contact_id"),
        deal_id=mapped.get("deal_id"),
        source_type=source_type,
        source_metadata=meta,
        structured_transcript=structured_transcript,
        mapping_method=map_method,
        external_interaction_id=ext_key,
        participants=plist,
        ai_intelligence=ai_intel,
    )
    log_audit_event(
        db,
        event_type="ingestion_completed",
        entity_table="crm_records",
        entity_id=record.id,
        detail={
            "job_id": ctx.job_id,
            "source_type": source_type,
            "external_interaction_id": ext_key,
            "mapping_method": map_method,
            "dedup_prior_count": int(prior_same_external),
        },
    )
    return TranscriptIngestResponse(
        job_id=ctx.job_id,
        status="accepted",
        record_id=record.id,
        account_id=mapped.get("account_id"),
        contact_id=mapped.get("contact_id"),
        deal_id=mapped.get("deal_id"),
        extracted=extracted,
        structured_transcript=structured_transcript,
        mapping_method=map_method,
        source_type=source_type,
    )


def build_audio_ingest_response(
    *,
    transcript: str,
    structured: StructuredTranscript | None,
    base: TranscriptIngestResponse,
) -> AudioIngestResponse:
    """Map unified pipeline output to audio response (flat transcript string)."""
    return AudioIngestResponse(
        transcript=transcript,
        job_id=base.job_id,
        status=base.status,
        record_id=base.record_id,
        account_id=base.account_id,
        contact_id=base.contact_id,
        deal_id=base.deal_id,
        extracted=base.extracted,
        structured_transcript=structured or base.structured_transcript,
        mapping_method=base.mapping_method,
        source_type=base.source_type,
    )
