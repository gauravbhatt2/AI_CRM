"""
Shared ingestion: Gemini extraction → CRM mapping → persist crm_record.
"""

from __future__ import annotations

import asyncio

from sqlalchemy.orm import Session

from app.db.crm_record_repository import create_crm_record
from app.ingestion.receiver import TranscriptReceiver
from app.models.ingestion import (
    AudioIngestResponse,
    ExtractedEntities,
    StructuredTranscript,
    TranscriptIngestResponse,
)
from app.services.extraction_service import extract_entities
from app.services.mapping_service import map_entities_to_crm


async def run_gemini_pipeline(
    *,
    transcript: str,
    db: Session,
    receiver: TranscriptReceiver,
    metadata: dict | None = None,
    external_id: str | None = None,
    source_type: str = "call",
    structured_transcript: StructuredTranscript | None = None,
) -> TranscriptIngestResponse:
    """Run extraction, mapping, and DB insert for a transcript string."""
    ctx = receiver.accept_transcript(
        content=transcript,
        metadata=metadata,
        external_id=external_id,
    )
    extracted_raw = await asyncio.to_thread(extract_entities, transcript)
    extracted = ExtractedEntities.model_validate(extracted_raw)
    mapped, map_method = map_entities_to_crm(transcript, extracted.model_dump(), db)
    record = create_crm_record(
        db,
        content=transcript,
        extracted=extracted,
        account_id=mapped.get("account_id"),
        contact_id=mapped.get("contact_id"),
        deal_id=mapped.get("deal_id"),
        source_type=source_type,
        source_metadata=metadata,
        structured_transcript=structured_transcript,
        mapping_method=map_method,
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
