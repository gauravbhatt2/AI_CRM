"""
Infer a speaker label per Whisper segment using Gemini (sales / prospect / names when obvious).
"""

from __future__ import annotations

import json
import logging
import re
import warnings
from typing import Any

with warnings.catch_warnings():
    warnings.simplefilter("ignore", category=FutureWarning)
    import google.generativeai as genai

from app.core.config import settings
from app.services.gemini_extraction import GEMINI_SAFETY_SETTINGS, extract_text_from_gemini_response

logger = logging.getLogger(__name__)

_CONFIGURED = False
_MAX_SEGMENTS = 100


def _ensure_configured() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    key = settings.gemini_api_key
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not set")
    genai.configure(api_key=key)
    _CONFIGURED = True


def _resolve_model_name(name: str) -> str:
    aliases = {
        "gemini-1.5-flash": "gemini-2.5-flash",
        "gemini-1.5-flash-8b": "gemini-2.5-flash",
        "gemini-1.5-pro": "gemini-2.5-pro",
    }
    return aliases.get(name.strip().lower(), name.strip())


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
        _ensure_configured()
    except RuntimeError:
        return segments

    raw_name = (settings.gemini_model or "").strip()
    if not raw_name:
        return segments

    model_name = _resolve_model_name(raw_name)
    prompt = f"""You label speakers in a sales call transcript given as JSON segments with start/end times.
For each segment, set "speaker" to a short label: e.g. "Sales", "Customer", or a first name if clearly inferable from the segment text.
Use consistent labels when the same party speaks across segments.
Return ONLY valid JSON: {{"segments": [{{"start": number, "end": number, "text": string, "speaker": string}}]}}
Input segments:
{json.dumps(trimmed, ensure_ascii=False)[:120000]}
"""

    try:
        model = genai.GenerativeModel(
            model_name,
            safety_settings=GEMINI_SAFETY_SETTINGS,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
            ),
        )
        response = model.generate_content(prompt)
        raw = extract_text_from_gemini_response(response)
    except Exception:
        logger.exception("Gemini speaker labeling failed")
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
