"""
Infer a speaker label per Whisper segment using Groq (sales / prospect / names when obvious).
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from openai import RateLimitError

from app.core.config import settings
from app.services.groq_llm import get_groq_client
from app.utils.groq_retry import groq_chat_with_retry

logger = logging.getLogger(__name__)

_MAX_SEGMENTS = 100


def _strip_markdown_fences(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```\s*$", "", text)
    return text.strip()


def label_segment_speakers(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Return a copy of segments with `speaker` filled (short labels like 'Rep', 'Prospect', or names).

    On any failure, returns the input segments unchanged.
    """
    if not segments:
        return segments
    trimmed = segments[:_MAX_SEGMENTS]
    try:
        get_groq_client()
    except RuntimeError:
        return segments

    if not (settings.groq_model or "").strip():
        return segments

    prompt = f"""You label speakers in a sales call transcript given as JSON segments with start/end times.
For each segment, set "speaker" to a short label: e.g. "Sales", "Customer", or a first name if clearly inferable from the segment text.
Use consistent labels when the same party speaks across segments.
Return ONLY valid JSON: {{"segments": [{{"start": number, "end": number, "text": string, "speaker": string}}]}}
Input segments:
{json.dumps(trimmed, ensure_ascii=False)[:120000]}
"""

    try:
        raw = groq_chat_with_retry(prompt, json_mode=True, max_attempts=2)
    except RateLimitError:
        logger.warning(
            "Groq speaker labeling skipped (rate limit). "
            "Set GROQ_LABEL_SPEAKERS=false to avoid this call.",
        )
        return segments
    except Exception:
        logger.exception("Groq speaker labeling failed")
        return segments

    if not raw:
        return segments
    try:
        parsed = json.loads(_strip_markdown_fences(raw))
    except (json.JSONDecodeError, TypeError, ValueError):
        logger.warning("Speaker JSON parse failed")
        return segments

    labeled = parsed.get("segments") if isinstance(parsed, dict) else None
    if not isinstance(labeled, list) or len(labeled) != len(trimmed):
        return segments

    out: list[dict[str, Any]] = []
    for i, orig in enumerate(trimmed):
        row = dict(orig)
        item = labeled[i]
        if isinstance(item, dict):
            sp = item.get("speaker")
            if isinstance(sp, str) and sp.strip():
                row["speaker"] = sp.strip()[:128]
        out.append(row)
    if len(segments) > _MAX_SEGMENTS:
        for extra in segments[_MAX_SEGMENTS:]:
            out.append(dict(extra))
    return out
