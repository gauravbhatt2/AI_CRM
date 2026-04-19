from typing import Any, Literal

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
        description="Optional client-supplied correlation id (stored as external_interaction_id)",
    )
    participants: list[str] | None = Field(
        default=None,
        description="Optional participant names/emails (DRD); merged with metadata.participants",
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
    """Structured fields extracted from the transcript or email body (LLM)."""

    budget: str = Field(default="", description="Numeric budget as string, or empty")
    intent: str = Field(default="", description="high | medium | low")
    competitors: list[str] = Field(default_factory=list, description="Named competitors")
    product: str = Field(default="", description="Clean product/service name")
    product_version: str = Field(default="", description="Version number or release identifier")
    timeline: str = Field(default="", description="Decision/implementation timeline phrase")
    industry: str = Field(default="", description="Industry vertical if mentioned")
    pain_points: str = Field(default="", description="Customer problems/frustrations as text")
    next_step: str = Field(default="", description="Agreed-upon or implied next step")
    urgency_reason: str = Field(default="", description="Why the request is time-sensitive")
    stakeholders: list[str] = Field(default_factory=list, description="People involved in the decision")
    mentioned_company: str = Field(default="", description="Company the customer represents")
    procurement_stage: str = Field(default="", description="e.g. evaluation, negotiation, budget approved")
    use_case: str = Field(default="", description="What the customer intends to use the product for")
    decision_criteria: str = Field(default="", description="What matters most to the buyer")
    budget_owner: str = Field(default="", description="Person who controls the budget")
    implementation_scope: str = Field(default="", description="Rollout scope — company-wide, regional, pilot")
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


class ExtractedFacts(BaseModel):
    """Phase-1 factual extraction: statements, entities, participants, timestamps (no scoring)."""

    statements: list[str] = Field(default_factory=list)
    entities: dict[str, Any] = Field(default_factory=dict)
    participants: list[str] = Field(default_factory=list)
    timestamps: list[dict[str, Any]] = Field(default_factory=list)


class TranscriptIngestResponse(BaseModel):
    """Transcript accepted; includes LLM extraction, CRM links, and DB row id."""

    job_id: str = Field(..., description="Internal job identifier for tracing")
    status: str = Field(default="accepted", description="Ingestion status")
    record_id: int = Field(..., description="Primary key of the saved row in crm_records")
    account_id: int | None = Field(default=None, description="Linked Account id")
    contact_id: int | None = Field(default=None, description="Linked Contact id")
    deal_id: int | None = Field(default=None, description="Linked Deal id")
    extracted: ExtractedEntities = Field(..., description="Structured CRM fields")
    extracted_facts: ExtractedFacts | None = Field(
        default=None,
        description="Phase-1 factual extraction (statements, entities, participants, timestamps)",
    )
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
    extracted: ExtractedEntities = Field(..., description="Structured CRM fields from LLM extraction")
    extracted_facts: ExtractedFacts | None = Field(
        default=None,
        description="Phase-1 factual extraction merged from transcript",
    )
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
    participants: list[str] | None = Field(
        default=None,
        description="Optional participant identifiers for unified timeline (DRD)",
    )
