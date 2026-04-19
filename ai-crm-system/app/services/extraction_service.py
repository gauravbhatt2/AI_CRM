"""
Business logic for AI-powered field extraction from transcripts.

Two-phase pipeline (see `groq_extraction.run_transcript_extraction_pipeline`):
1) Facts-only extraction — single Groq call on the transcript (truncated if extremely long)
2) Evaluation from merged facts only (Groq JSON)
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Phase 1 — factual extraction only (no intent, pain, scoring)
# ---------------------------------------------------------------------------

FACTS_EXTRACTION_PROMPT_TEMPLATE = """You extract ONLY factual information from conversation text.

OUTPUT: One JSON object only. No markdown fences, no commentary.

RULES:
- No interpretation, opinion, or inference beyond what is explicitly stated.
- Do NOT output intent, pain_points, deal_score, risk, summary, or next_action.
- Quote or closely paraphrase important lines as factual "statements" (key claims, numbers, names, commitments).
- "entities" holds normalized factual fields (company, product, budget, etc.).
- "participants": people or roles named (e.g. "Jane", "VP Sales") when stated.
- "timestamps": only if the text includes explicit times/dates; else []. Each item: {{"label": "string", "start_sec": number|null, "end_sec": number|null}} or use {{"note": "Q4 2025"}} when wall-clock unknown.

MISSING: use "n/a" for unknown string fields; budget use integer when clearly stated else "n/a"; arrays empty when absent.

REQUIRED SHAPE:
{
  "statements": [],
  "entities": {
    "mentioned_company": "n/a",
    "product": "n/a",
    "product_version": "n/a",
    "budget": "n/a",
    "competitors": [],
    "industry": "n/a",
    "timeline": "n/a",
    "stakeholders": [],
    "procurement_stage": "n/a",
    "use_case": "n/a",
    "decision_criteria": "n/a",
    "budget_owner": "n/a",
    "implementation_scope": "n/a",
    "custom_fields": {}
  },
  "participants": [],
  "timestamps": []
}

--- TRANSCRIPT ---
{transcript}"""

# ---------------------------------------------------------------------------
# Phase 2 — evaluation from merged facts JSON only (no raw transcript)
# ---------------------------------------------------------------------------

EVALUATION_PROMPT_TEMPLATE = """You evaluate a sales/support interaction using ONLY the JSON object below (merged factual extraction). Do not invent details not supported by these facts.

OUTPUT: One JSON object only. No markdown fences, no commentary.

If evidence is insufficient for a field, use "n/a", 0, or [] as appropriate.

REQUIRED KEYS:
{
  "intent": "high|medium|low",
  "pain_points": "n/a",
  "next_step": "n/a",
  "next_action": "n/a",
  "risk_level": "low|medium|high",
  "risk_reason": "n/a",
  "deal_score": 0,
  "interaction_type": "sales|support|inquiry|complaint",
  "summary": "n/a",
  "tags": [],
  "urgency_reason": "n/a"
}

Rules:
- next_action: max 12 words, imperative verb first.
- summary: brief (one or two sentences), grounded in the facts only.

MERGED_FACTS_JSON:
{merged_facts}"""

TRANSCRIPT_LLM_MAX_CHARS = 120_000


def build_facts_extraction_prompt(transcript: str) -> str:
    t = (transcript or "").strip()
    if len(t) > TRANSCRIPT_LLM_MAX_CHARS:
        t = (
            t[: TRANSCRIPT_LLM_MAX_CHARS // 2]
            + "\n\n[... middle omitted for length ...]\n\n"
            + t[-(TRANSCRIPT_LLM_MAX_CHARS // 2) :]
        )
    return FACTS_EXTRACTION_PROMPT_TEMPLATE.replace("{transcript}", t)


def build_evaluation_prompt(merged_facts_json: str) -> str:
    return EVALUATION_PROMPT_TEMPLATE.replace("{merged_facts}", (merged_facts_json or "").strip()[:28000])


def build_unified_extraction_prompt(transcript: str) -> str:
    """Backward-compatible alias: facts-only prompt (same as phase 1)."""
    return build_facts_extraction_prompt(transcript)


def build_extraction_prompt(transcript: str) -> str:
    """Backward-compatible alias."""
    return build_facts_extraction_prompt(transcript)


def extract_transcript_bundle(
    text: str, context: dict[str, Any] | None = None
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Run two-phase pipeline (facts + evaluation); returns (extracted_entities, ai_intelligence, merged_extracted_facts)."""
    _ = context
    from app.services.groq_extraction import run_transcript_extraction_pipeline

    return run_transcript_extraction_pipeline(text)


def extract_entities(text: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Extract CRM fields (same shape as before); facts bundle available via extract_transcript_bundle."""
    entities, _, _ = extract_transcript_bundle(text, context=context)
    return entities


class ExtractionService:
    """Coordinates extraction from normalized text via Groq."""

    def extract_entities(self, text: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        return extract_entities(text, context=context)

    def preview(self, text: str) -> dict[str, Any]:
        entities, ai, facts = extract_transcript_bundle(text)
        return {
            "text_length": len(text),
            "entities": entities,
            "ai_intelligence": ai,
            "extracted_facts": facts,
        }
