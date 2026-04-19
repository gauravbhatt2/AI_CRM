"""
Shared ingestion: Groq extraction → CRM mapping → persist crm_record.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.audit_repository import log_audit_event
from app.db.crm_record_repository import create_crm_record
from app.db.models import CrmRecord
from app.ingestion.receiver import TranscriptReceiver
from app.models.ingestion import (
    AudioIngestResponse,
    ExtractedEntities,
    ExtractedFacts,
    StructuredTranscript,
    TranscriptIngestResponse,
)
from app.agents.followup_agent import generate_followup_email
from app.agents.next_action_agent import suggest_next_action
from app.services.extraction_service import extract_transcript_bundle
from app.services.mapping_service import map_entities_to_crm


def _build_agent_record_dict(
    transcript: str,
    extracted_dump: dict[str, Any],
    ai_intel: dict[str, Any] | None,
) -> dict[str, Any]:
    merged = {**dict(extracted_dump), **dict(ai_intel or {})}
    merged["content"] = transcript
    return merged


def _run_post_extract_agents(record_dict: dict[str, Any]) -> tuple[str, str]:
    return suggest_next_action(record_dict), generate_followup_email(record_dict)


def _merge_participants(
    meta: dict,
    explicit: list[str] | None,
    *,
    from_facts: list[str] | None = None,
) -> list[str]:
    """DRD participants: union of explicit list, metadata.participants, and optional facts-derived names."""
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
    if from_facts:
        for p in from_facts:
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

    extracted_raw, ai_intel, merged_facts = await asyncio.to_thread(extract_transcript_bundle, transcript)
    meta["extracted_facts"] = merged_facts
    facts_pf = merged_facts.get("participants") if isinstance(merged_facts.get("participants"), list) else []
    plist = _merge_participants(meta, participants, from_facts=facts_pf)
    extracted = ExtractedEntities.model_validate(extracted_raw)
    record_dict = _build_agent_record_dict(transcript, extracted.model_dump(), ai_intel)
    agent_next, followup_email = await asyncio.to_thread(_run_post_extract_agents, record_dict)
    ai_intel_merged = {**(ai_intel or {}), "next_action": agent_next}

    mapped, map_method = map_entities_to_crm(
        transcript,
        extracted.model_dump(),
        db,
        source_metadata=meta,
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
        ai_intelligence=ai_intel_merged,
        followup_email=followup_email,
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

    try:
        from app.services.scheduler import schedule_followup

        intent_norm = str(extracted.intent or "").strip().lower()
        if intent_norm == "high":
            schedule_followup(record.id, 30)
        elif intent_norm == "medium":
            schedule_followup(record.id, 1440)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Scheduled follow-up not registered: %s", exc)

    try:
        facts_model = ExtractedFacts.model_validate(merged_facts)
    except Exception:
        facts_model = None

    return TranscriptIngestResponse(
        job_id=ctx.job_id,
        status="accepted",
        record_id=record.id,
        account_id=mapped.get("account_id"),
        contact_id=mapped.get("contact_id"),
        deal_id=mapped.get("deal_id"),
        extracted=extracted,
        extracted_facts=facts_model,
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
        extracted_facts=base.extracted_facts,
        structured_transcript=structured or base.structured_transcript,
        mapping_method=base.mapping_method,
        source_type=base.source_type,
    )
