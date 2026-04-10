"""
Business logic for AI-powered field extraction from transcripts.

Prompt text lives here; Gemini execution and JSON parsing live in `gemini_extraction`.
"""

from typing import Any

# Full prompt sent to Gemini. Placeholder {transcript} is replaced with the conversation text.
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

Return ONLY valid JSON in this exact format:

{
  "budget": "",
  "intent": "",
  "competitors": [],
  "product": "",
  "timeline": "",
  "industry": "",
  "custom_fields": {}
}

Conversation:
{transcript}"""


def build_extraction_prompt(transcript: str) -> str:
    """Build the user message for Gemini from the template and transcript."""
    return EXTRACTION_PROMPT_TEMPLATE.replace("{transcript}", transcript.strip())


def extract_entities(text: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Extract CRM-oriented entities via Gemini using `build_extraction_prompt`."""
    _ = context
    from app.services.gemini_extraction import execute_gemini_json_extraction

    return execute_gemini_json_extraction(build_extraction_prompt(text))


class ExtractionService:
    """Coordinates extraction from normalized text via Gemini."""

    def extract_entities(self, text: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Extract CRM-oriented entities; `context` reserved for future use."""
        return extract_entities(text, context=context)

    def preview(self, text: str) -> dict[str, Any]:
        """Dry-run extraction for API previews."""
        entities = extract_entities(text)
        return {"text_length": len(text), "entities": entities}
