"""
Business logic for AI-powered field extraction from transcripts.

Prompt text lives here; Groq execution and JSON parsing live in `groq_extraction`.
"""

from typing import Any

# Full prompt sent to Groq. Placeholder {transcript} is replaced with the conversation text.
EXTRACTION_PROMPT_TEMPLATE = """You are an AI system that extracts structured CRM data from sales conversations, emails, or meeting notes.

Extract the following core fields:
- budget (numeric string if possible, else descriptive range)
- intent (low, medium, high, or a short phrase)
- competitors (list of company names)
- product (product or solution discussed)
- timeline (timeframe or deadline if mentioned)
- industry (company industry / vertical if mentioned, else empty string)

Also populate "custom_fields" with up to 20 additional string key-value pairs useful for CRM
(deal qualifiers, pain points, tech stack, team size, procurement stage, renewal date, etc.).
Only include keys where you have evidence in the text. Use short snake_case keys.
If nothing extra applies, return an empty object {{}}.

Return ONLY valid JSON in this exact format (top-level keys — do not nest under another object):

{
  "budget": "",
  "intent": "",
  "competitors": [],
  "product": "",
  "timeline": "",
  "industry": "",
  "custom_fields": {}
}

Infer intent (e.g. low / medium / high or a short phrase) from tone and buying signals when numbers are not stated.
If the dialogue is very short, still set intent when there is any sales or discovery context; leave other fields empty only when unsupported.

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
