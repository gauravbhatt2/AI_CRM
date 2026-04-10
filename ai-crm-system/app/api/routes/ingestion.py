import asyncio
import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import settings
from app.ingestion.receiver import TranscriptReceiver
from app.models.ingestion import (
    AudioIngestResponse,
    InteractionIngestRequest,
    StructuredTranscript,
    TranscriptIngestRequest,
    TranscriptIngestResponse,
)
from app.services.gemini_speakers import label_segment_speakers
from app.services.ingestion_pipeline import build_audio_ingest_response, run_gemini_pipeline
from app.services.transcription_service import WhisperNotInstalledError, transcribe_audio_detailed

router = APIRouter(prefix="/ingest", tags=["ingestion"])

_receiver = TranscriptReceiver()


def _require_gemini() -> None:
    if not settings.gemini_api_key:
        raise HTTPException(
            status_code=503,
            detail="GEMINI_API_KEY is not configured. Set it in the environment or .env file.",
        )
    if not (settings.gemini_model or "").strip():
        raise HTTPException(
            status_code=503,
            detail=(
                "GEMINI_MODEL is not configured. Set it in the environment or .env file "
                "(e.g. GEMINI_MODEL=gemini-2.5-flash) to choose which Gemini model to use."
            ),
        )


@router.post("/transcript", response_model=TranscriptIngestResponse)
async def ingest_transcript(
    body: TranscriptIngestRequest,
    db: Session = Depends(get_db),
) -> TranscriptIngestResponse:
    """
    Accept a transcript, run Gemini extraction, and return structured CRM fields.
    """
    _require_gemini()
    return await run_gemini_pipeline(
        transcript=body.content,
        db=db,
        receiver=_receiver,
        metadata=body.metadata,
        external_id=body.external_id,
        source_type=body.source_type,
    )


@router.post("/interaction", response_model=TranscriptIngestResponse)
async def ingest_interaction(
    body: InteractionIngestRequest,
    db: Session = Depends(get_db),
) -> TranscriptIngestResponse:
    """
    Ingest text from email, SMS, meetings, CRM webhooks, or calls — same pipeline as `/transcript`.
    """
    _require_gemini()
    meta = dict(body.metadata or {})
    return await run_gemini_pipeline(
        transcript=body.content,
        db=db,
        receiver=_receiver,
        metadata=meta,
        external_id=body.external_id,
        source_type=body.source_type,
    )


@router.post("/audio", response_model=AudioIngestResponse)
async def ingest_audio(
    file: UploadFile = File(
        ...,
        description="Audio or video file (wav, mp3, m4a, mp4 with audio, etc.)",
    ),
    db: Session = Depends(get_db),
) -> AudioIngestResponse:
    """
    Upload audio or video, transcribe with Whisper (timestamped segments), optional speaker labels,
    then run the same extraction + CRM pipeline as `/ingest/transcript`.
    """
    _require_gemini()

    suffix = Path(file.filename or "audio.wav").suffix
    if not suffix or len(suffix) > 10:
        suffix = ".wav"

    fd, tmp_path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    try:
        data = await file.read()
        if not data:
            raise HTTPException(status_code=400, detail="Empty file upload.")
        with open(tmp_path, "wb") as out:
            out.write(data)

        try:
            detail = await asyncio.to_thread(transcribe_audio_detailed, tmp_path)
        except WhisperNotInstalledError as e:
            raise HTTPException(status_code=503, detail=str(e)) from e

        plain = (detail.get("plain_text") or "").strip()
        if not plain:
            raise HTTPException(
                status_code=422,
                detail="Transcription was empty. Check audio quality or format (FFmpeg may be required).",
            )

        segments = detail.get("segments") or []
        try:
            labeled = await asyncio.to_thread(label_segment_speakers, segments)
        except Exception:
            labeled = segments

        structured = StructuredTranscript(plain_text=plain, segments=labeled or [])

        base = await run_gemini_pipeline(
            transcript=plain,
            db=db,
            receiver=_receiver,
            metadata={"filename": file.filename},
            external_id=None,
            source_type="call",
            structured_transcript=structured,
        )
        return build_audio_ingest_response(
            transcript=plain,
            structured=structured,
            base=base,
        )
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
