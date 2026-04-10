"""
Receive and validate transcripts or file references for the processing pipeline.

Downstream steps: transcription (if audio) → extraction → mapping → persistence.
"""

import uuid

from pydantic import BaseModel, Field


class IngestContext(BaseModel):
    """Internal context after a transcript is accepted."""

    job_id: str = Field(..., description="Correlation id for async processing")
    content_preview: str = Field(..., description="Short preview for logging")


class TranscriptReceiver:
    """Entry point for transcript ingestion (HTTP layer delegates here)."""

    def accept_transcript(
        self,
        content: str,
        metadata: dict[str, str | int | float | bool | None] | None = None,
        external_id: str | None = None,
    ) -> IngestContext:
        """
        Accept a transcript for processing.

        Persists to queue/DB in a future iteration; returns a placeholder job id.
        """
        _ = metadata, external_id  # reserved for tracing and deduplication
        job_id = str(uuid.uuid4())
        preview = content[:200] + ("…" if len(content) > 200 else "")
        return IngestContext(job_id=job_id, content_preview=preview)
