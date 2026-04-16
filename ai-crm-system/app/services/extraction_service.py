"""
Business logic for AI-powered field extraction from transcripts.

Prompt text lives here; Groq execution and JSON parsing live in `groq_extraction`.
"""

from typing import Any

# ---------------------------------------------------------------------------
# Extraction prompt — strict 17-field CRM schema
# ---------------------------------------------------------------------------

EXTRACTION_PROMPT_TEMPLATE = """You are a precision CRM extraction engine for noisy Whisper transcripts.
Read the conversation carefully and return ONE flat JSON object with exactly the 17 keys listed.

ABSOLUTE RULES:
1) Return STRICT JSON only. No markdown, no prose, no code fences.
2) Use only evidence from the conversation. Never infer facts that are not stated.
3) If a field is missing, ambiguous, or conflicting, return null (or [] for array fields).
4) Include every required key exactly once. Do not add extra keys.
5) Keep values concise and CRM-ready (short phrases, not paragraphs).

CONFIDENCE AND EVIDENCE:
- Prefer precision over coverage: leave unknown fields null.
- Do not invent names, titles, companies, numbers, dates, or stages.
- If multiple possibilities exist and no clear winner is stated, return null.

WHISPER / ASR HANDLING:
- Transcript may contain filler words, minor transcription errors, and missing punctuation.
- Normalize obvious ASR noise before extraction (e.g., repeated words, disfluencies).
- Use context from surrounding lines to resolve entity boundaries.
- If speaker labels or timestamps appear, use them as context only; do not copy timestamps into values.
- Never include trailing connector words in entities (e.g., "Novagen is" must become "Novagen").

FIELD RULES:
- budget:
  - Return integer only (no symbols, commas, words).
  - Valid conversions: "$75,000" -> 75000, "50k" -> 50000, "1.2M" -> 1200000.
  - If plain currency amount appears (e.g., "$99", "99 dollars"), keep exact value (99).
  - For consumer automotive map-update calls, if ASR produces "$99,000" but nearby context includes promotions like "$50 off" and shipping/tax, normalize to 99.
  - If only vague wording exists (e.g., "six figures", "large budget"), return null.
- intent:
  - Must be exactly one of "high", "medium", "low".
  - high = clear commitment or purchase readiness.
  - medium = active evaluation/comparison with next steps.
  - low = exploratory discussion with no urgency/commitment.
  - If unclear, use "medium".
- timeline:
  - Capture only decision/implementation timeline.
  - Ignore shipping/delivery/admin scheduling.
  - If absent, return null.
- product and product_version:
  - product = clean product/service name only.
  - product_version = version only (examples: "7.7", "2024.1"), else null.
  - Never place version text inside product.
- competitors:
  - Array of competitor company names only.
  - Normalize casing to proper names and deduplicate.
- stakeholders:
  - Array of names or role titles involved in decision/approval.
  - Prefer "Name (Role)" when both are present.
  - Do not include generic words like "team" unless explicitly the only reference.
- next_step:
  - Must be a concrete agreed action (meeting, demo, proposal, follow-up), not a wish.
- procurement_stage:
  - Use only if clearly stated/implied by explicit evidence (e.g., "evaluation", "negotiation", "legal review", "budget approved").
  - Otherwise null.

OUTPUT SCHEMA (EXACT KEYS ONLY):
{
  "budget": null,
  "intent": "medium",
  "timeline": null,
  "product": null,
  "product_version": null,
  "competitors": [],
  "industry": null,
  "pain_points": null,
  "next_step": null,
  "urgency_reason": null,
  "stakeholders": [],
  "mentioned_company": null,
  "procurement_stage": null,
  "use_case": null,
  "decision_criteria": null,
  "budget_owner": null,
  "implementation_scope": null
}

Field definitions:
  budget               -> integer or null
  intent               -> "high" | "medium" | "low"
  timeline             -> decision/implementation timeline phrase, or null
  product              -> product/service name, or null
  product_version      -> version string, or null
  competitors          -> array of competitor names
  industry             -> industry vertical, or null
  pain_points          -> main customer problems, single concise string, or null
  next_step            -> concrete agreed next action, or null
  urgency_reason       -> reason for urgency/time pressure, or null
  stakeholders         -> array of decision participants (names/roles; use "Name (Role)" when possible)
  mentioned_company    -> customer company name, or null
  procurement_stage    -> buying stage, or null
  use_case             -> intended usage, or null
  decision_criteria    -> key evaluation criteria, or null
  budget_owner         -> person/role controlling budget, or null
  implementation_scope -> rollout scope, or null

Conversation:
{transcript}"""

# Avoid huge prompts starving JSON output or hitting edge cases with JSON mode.
TRANSCRIPT_LLM_MAX_CHARS = 120_000


def build_extraction_prompt(transcript: str) -> str:
    """Build the user message for Groq from the template and transcript."""
    t = transcript.strip()
    if len(t) > TRANSCRIPT_LLM_MAX_CHARS:
        t = (
            t[: TRANSCRIPT_LLM_MAX_CHARS // 2]
            + "\n\n[... middle of transcript omitted for length ...]\n\n"
            + t[-(TRANSCRIPT_LLM_MAX_CHARS // 2) :]
        )
    return EXTRACTION_PROMPT_TEMPLATE.replace("{transcript}", t)


def extract_entities(text: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Extract CRM-oriented entities via Groq using `build_extraction_prompt`."""
    _ = context
    from app.services.groq_extraction import execute_groq_json_extraction

    return execute_groq_json_extraction(
        build_extraction_prompt(text),
        source_transcript=text,
    )


class ExtractionService:
    """Coordinates extraction from normalized text via Groq."""

    def extract_entities(self, text: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Extract CRM-oriented entities; `context` reserved for future use."""
        return extract_entities(text, context=context)

    def preview(self, text: str) -> dict[str, Any]:
        """Dry-run extraction for API previews."""
        entities = extract_entities(text)
        return {"text_length": len(text), "entities": entities}
