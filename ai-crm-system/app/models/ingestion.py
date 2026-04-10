from typing import Literal

from pydantic import BaseModel, Field, field_validator


class TranscriptIngestRequest(BaseModel):
    """Inbound transcript payload for CRM processing pipeline."""

    content: str = Field(..., min_length=1, description="Raw transcript text")
    metadata: dict[str, str | int | float | bool | None] | None = Field(
        default=None,
        description="Optional metadata (source, language, call_id, etc.)",
    )
    external_id: str | None = Field(
        default=None,
        description="Optional client-supplied correlation id",
    )
    source_type: Literal["call", "email", "meeting", "sms", "crm_update"] = Field(
        default="call",
        description="How this text was captured (for Revenue Graph / audit trail)",
    )


class TranscriptSegment(BaseModel):
    """Single timed slice of a transcript (Whisper + optional speaker label)."""

    start: float = 0.0
    end: float = 0.0
    text: str = ""
    speaker: str | None = None


class StructuredTranscript(BaseModel):
    """Timestamped segments; plain_text is the canonical search string."""

    plain_text: str = ""
    segments: list[TranscriptSegment] = Field(default_factory=list)


class ExtractedEntities(BaseModel):
    """Structured fields extracted from the transcript or email body (Gemini)."""

    budget: str = Field(default="", description="Budget signal or range if mentioned")
    intent: str = Field(default="", description="Buyer intent / stage")
    competitors: list[str] = Field(default_factory=list, description="Named competitors")
    product: str = Field(default="", description="Product or solution discussed")
    timeline: str = Field(default="", description="Timing / deadline if mentioned")
    industry: str = Field(default="", description="Industry vertical if mentioned")
    custom_fields: dict[str, str] = Field(
        default_factory=dict,
        description="Up to 20 CRM-specific string fields (deal qualifiers, etc.)",
    )

    @field_validator("custom_fields")
    @classmethod
    def limit_custom_fields(cls, v: dict[str, str]) -> dict[str, str]:
        if not isinstance(v, dict):
            return {}
        out: dict[str, str] = {}
        for i, (k, val) in enumerate(v.items()):
            if i >= 20:
                break
            ks = str(k).strip()
            if not ks:
                continue
            out[ks[:128]] = str(val).strip()[:2048]
        return out


class TranscriptIngestResponse(BaseModel):
    """Transcript accepted; includes Gemini extraction, CRM links, and DB row id."""

    job_id: str = Field(..., description="Internal job identifier for tracing")
    status: str = Field(default="accepted", description="Ingestion status")
    record_id: int = Field(..., description="Primary key of the saved row in crm_records")
    account_id: int | None = Field(default=None, description="Linked Account id")
    contact_id: int | None = Field(default=None, description="Linked Contact id")
    deal_id: int | None = Field(default=None, description="Linked Deal id")
    extracted: ExtractedEntities = Field(..., description="Structured CRM fields")
    structured_transcript: StructuredTranscript | None = Field(
        default=None,
        description="Timed segments (and speakers when available)",
    )
    mapping_method: str = Field(
        default="rules",
        description="crm resolution path: llm, rules, or llm+rules",
    )
    source_type: str = Field(default="call", description="Ingestion channel")


class AudioIngestResponse(BaseModel):
    """Audio ingested via Whisper, then same pipeline as text ingestion."""

    transcript: str = Field(..., description="Text produced by Whisper from the audio file")
    job_id: str = Field(..., description="Internal job identifier for tracing")
    status: str = Field(default="accepted", description="Ingestion status")
    record_id: int = Field(..., description="Primary key of the saved row in crm_records")
    account_id: int | None = Field(default=None, description="Linked Account id")
    contact_id: int | None = Field(default=None, description="Linked Contact id")
    deal_id: int | None = Field(default=None, description="Linked Deal id")
    extracted: ExtractedEntities = Field(..., description="Structured CRM fields from Gemini")
    structured_transcript: StructuredTranscript | None = Field(
        default=None,
        description="Whisper segments with timestamps and inferred speakers",
    )
    mapping_method: str = Field(default="rules")
    source_type: str = Field(default="call")


class InteractionIngestRequest(BaseModel):
    """
    Webhook-style ingestion for automated capture (email, meeting notes, SMS, CRM events).

    Integrations push content here; the same extraction + mapping pipeline runs as for calls.
    """

    source_type: Literal["email", "meeting", "sms", "crm_update", "call"] = Field(
        ...,
        description="Channel identifier",
    )
    content: str = Field(..., min_length=1, description="Plain text body or transcript")
    metadata: dict[str, str | int | float | bool | None] | None = Field(
        default=None,
        description="e.g. subject, from, to, message_id, calendar_id, external_record_id",
    )
    external_id: str | None = Field(default=None, description="Idempotency / correlation id")
