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
from app.db.crm_record_repository import (
    update_crm_record_content,
    update_crm_record_structured_transcript,
)
from app.services.groq_speakers import (
    heuristic_speaker_segments,
    label_segment_speakers,
    maybe_relabel_speakers_ab,
)
from app.services.ingestion_pipeline import build_audio_ingest_response, run_transcript_pipeline
from app.services.speaker_diarization import apply_pyannote_to_segments
from app.services.transcription_service import (
    FfmpegRequiredError,
    WhisperNotInstalledError,
    transcribe_audio_detailed,
)


def _rebuild_plain_text_from_segments(segments: list[dict]) -> str:
    parts = [str(s.get("text") or "").strip() for s in segments if isinstance(s, dict)]
    return " ".join(p for p in parts if p).strip()


def _copy_segments(segments: list) -> list[dict]:
    return [dict(s) for s in segments if isinstance(s, dict)]


router = APIRouter(prefix="/ingest", tags=["ingestion"])

_receiver = TranscriptReceiver()


def _transcript_with_speaker_labels(structured: StructuredTranscript, fallback: str) -> str:
    """Build readable lines like '[00:05-00:09] Sales: ...' from labeled segments."""
    def _fmt_ts(sec: float | int | None) -> str:
        try:
            s = max(0, int(float(sec or 0)))
        except (TypeError, ValueError):
            s = 0
        m, r = divmod(s, 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h:02d}:{m:02d}:{r:02d}"
        return f"{m:02d}:{r:02d}"

    segs = structured.segments or []
    if not segs:
        return fallback
    lines: list[str] = []
    for seg in segs:
        t = (seg.text or "").strip()
        if not t:
            continue
        sp = (seg.speaker or "").strip()
        start = _fmt_ts(getattr(seg, "start", 0.0))
        end = _fmt_ts(getattr(seg, "end", 0.0))
        prefix = f"[{start}-{end}]"
        lines.append(f"{prefix} {sp}: {t}" if sp else f"{prefix} {t}")
    return "\n".join(lines) if lines else fallback


def _require_groq() -> None:
    if not settings.groq_api_key:
        raise HTTPException(
            status_code=503,
            detail="GROQ_API_KEY is not configured. Set it in the environment or .env file.",
        )
    if not (settings.groq_model or "").strip():
        raise HTTPException(
            status_code=503,
            detail=(
                "GROQ_MODEL is not configured. Set it in the environment or .env file "
                "(e.g. GROQ_MODEL=llama-3.3-70b-versatile)."
            ),
        )


@router.post("/transcript", response_model=TranscriptIngestResponse)
async def ingest_transcript(
    body: TranscriptIngestRequest,
    db: Session = Depends(get_db),
) -> TranscriptIngestResponse:
    """
    Accept a transcript, run Groq extraction, and return structured CRM fields.
    """
    _require_groq()
    meta = dict(body.metadata or {})
    meta.setdefault("source_type", body.source_type)
    return await run_transcript_pipeline(
        transcript=body.content,
        db=db,
        receiver=_receiver,
        metadata=meta,
        external_id=body.external_id,
        participants=body.participants,
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
    _require_groq()
    meta = dict(body.metadata or {})
    meta.setdefault("source_type", body.source_type)
    return await run_transcript_pipeline(
        transcript=body.content,
        db=db,
        receiver=_receiver,
        metadata=meta,
        external_id=body.external_id,
        participants=body.participants,
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
    _require_groq()

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
        except FfmpegRequiredError as e:
            raise HTTPException(status_code=503, detail=str(e)) from e

        segments = _copy_segments(detail.get("segments") or [])
        pyannote_applied = False
        try:
            segments, pyannote_applied = await asyncio.to_thread(
                apply_pyannote_to_segments,
                tmp_path,
                segments,
            )
        except Exception:
            pyannote_applied = False

        plain = _rebuild_plain_text_from_segments(segments).strip() or (detail.get("plain_text") or "").strip()
        if not plain:
            raise HTTPException(
                status_code=422,
                detail="Transcription was empty. Check audio quality or format (FFmpeg may be required).",
            )

        structured = StructuredTranscript(plain_text=plain, segments=segments or [])

        base = await run_transcript_pipeline(
            transcript=plain,
            db=db,
            receiver=_receiver,
            metadata={"filename": file.filename},
            external_id=None,
            source_type="call",
            structured_transcript=structured,
        )

        out_structured = structured
        if segments:
            try:
                if pyannote_applied:
                    labeled = [dict(s) for s in segments]
                elif settings.groq_label_speakers:
                    labeled = await asyncio.to_thread(label_segment_speakers, segments)
                else:
                    labeled = await asyncio.to_thread(heuristic_speaker_segments, segments)
                labeled = maybe_relabel_speakers_ab(labeled or segments)
                out_structured = StructuredTranscript(
                    plain_text=plain,
                    segments=labeled or segments,
                )
                update_crm_record_structured_transcript(
                    db,
                    base.record_id,
                    out_structured,
                )
            except Exception:
                out_structured = structured

        has_speakers = any(
            (seg.speaker or "").strip() for seg in (out_structured.segments or [])
        )
        display_transcript = (
            _transcript_with_speaker_labels(out_structured, plain)
            if has_speakers
            else plain
        )
        if has_speakers and display_transcript != plain:
            update_crm_record_content(db, base.record_id, display_transcript)

        return build_audio_ingest_response(
            transcript=display_transcript,
            structured=out_structured,
            base=base,
        )
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
