"""
Business logic for AI-powered field extraction from transcripts.

Prompt text lives here; Groq execution and JSON parsing live in `groq_extraction`.
"""

from typing import Any

# ---------------------------------------------------------------------------
# Extraction prompt — strict 17-field CRM schema
# ---------------------------------------------------------------------------

EXTRACTION_PROMPT_TEMPLATE = """You are a CRM data extraction engine. Your ONLY job is to read the
conversation below and return a single flat JSON object with exactly the keys listed. Nothing else.

═══════════════════════════════════════════════════════════════════════════════
HARD RULES — FOLLOW EVERY ONE
═══════════════════════════════════════════════════════════════════════════════
1. Return STRICT JSON only. No markdown fences, no explanations, no extra text.
2. DO NOT hallucinate. If information is NOT in the text → return null for that field.
3. Never invent names, companies, numbers, or dates that are not explicitly stated.
4. Every key below MUST appear in your output. Use null when the value is unknown.
5. No extra keys beyond the 17 listed below.

═══════════════════════════════════════════════════════════════════════════════
BUDGET RULES
═══════════════════════════════════════════════════════════════════════════════
• Always return an integer (no currency symbols, no commas, no strings).
  "$75,000" → 75000  |  "50k" → 50000  |  "$1.2M" → 1200000
• If only a vague range like "six figures" → estimate the midpoint as an integer.
• If NO budget is mentioned at all → null.

═══════════════════════════════════════════════════════════════════════════════
INTENT RULES
═══════════════════════════════════════════════════════════════════════════════
Return EXACTLY one of these three strings (lowercase):
  "high"   → strong buying intent, clear commitment, ready to purchase
  "medium" → evaluating, comparing options, asking for proposals
  "low"    → exploratory, no urgency, just gathering info
If uncertain, lean toward "medium". Never return any other value.

═══════════════════════════════════════════════════════════════════════════════
TIMELINE RULES (CRITICAL)
═══════════════════════════════════════════════════════════════════════════════
Extract ONLY the decision or implementation timeline.
IGNORE logistics / shipping / delivery phrases:
  ✗ "ship today" ✗ "send tomorrow" ✗ "deliver next week" ✗ "mail the invoice"
Valid examples:
  ✓ "we plan to implement next quarter"
  ✓ "decision by end of month"
  ✓ "need this live before Q3"
If no decision/implementation timeline exists → null.

═══════════════════════════════════════════════════════════════════════════════
PRODUCT + VERSION SEPARATION
═══════════════════════════════════════════════════════════════════════════════
"product" = clean product or service name (human-readable, CRM-friendly).
"product_version" = version number only (e.g. "7.7", "2024.1"), or null.
Example: "map update version 7.7" → product: "map update", product_version: "7.7"
Never put a version number inside the product field.

═══════════════════════════════════════════════════════════════════════════════
COMPETITOR RULES
═══════════════════════════════════════════════════════════════════════════════
• Normalize to official company names. "SF" or "salesforce" → "Salesforce".
• Deduplicate — no repeats in the array.

═══════════════════════════════════════════════════════════════════════════════
OUTPUT FORMAT — exactly these 17 keys, nothing more
═══════════════════════════════════════════════════════════════════════════════
{{
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
}}

Field definitions:
  budget              — integer or null
  intent              — "high" | "medium" | "low"
  timeline            — decision/implementation timeline phrase, or null
  product             — clean product/service name, or null
  product_version     — version string, or null
  competitors         — array of normalized competitor names
  industry            — industry vertical string, or null
  pain_points         — customer problems/frustrations as a single string, or null
  next_step           — agreed-upon next step, or null
  urgency_reason      — why time-sensitive, or null
  stakeholders        — array of names/roles involved in the decision
  mentioned_company   — company the customer represents, or null
  procurement_stage   — e.g. "evaluation", "negotiation", "budget approved", or null
  use_case            — what the customer intends to use the product for, or null
  decision_criteria   — what matters most (price, features, support…), or null
  budget_owner        — person who controls the budget, or null
  implementation_scope — rollout scope (e.g. "company-wide", "regional", "pilot"), or null

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
