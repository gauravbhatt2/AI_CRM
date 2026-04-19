"""Small Groq text completions for agents (non-JSON)."""

from __future__ import annotations

import logging

from app.utils.groq_retry import groq_chat_with_retry

logger = logging.getLogger(__name__)


def groq_text_or_none(prompt: str, *, max_tokens: int = 256, temperature: float = 0.2) -> str | None:
    """Return stripped assistant text, or None if Groq is unavailable or fails."""
    try:
        raw = groq_chat_with_retry(
            prompt,
            json_mode=False,
            max_attempts=2,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except Exception as exc:  # noqa: BLE001 — demo: never break pipeline on LLM
        logger.warning("Agent Groq call skipped: %s", exc)
        return None
    s = (raw or "").strip()
    return s or None
