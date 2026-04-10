"""
Gemini execution for CRM extraction: JSON-only responses and defensive parsing.

Prompt construction lives in `extraction_service` (see `build_extraction_prompt`).
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

from google.generativeai.types import HarmBlockThreshold, HarmCategory

from app.core.config import settings

logger = logging.getLogger(__name__)

# Default SDK thresholds can block benign sales transcripts; only block high-severity content.
GEMINI_SAFETY_SETTINGS = [
    {"category": HarmCategory.HARM_CATEGORY_HARASSMENT, "threshold": HarmBlockThreshold.BLOCK_ONLY_HIGH},
    {"category": HarmCategory.HARM_CATEGORY_HATE_SPEECH, "threshold": HarmBlockThreshold.BLOCK_ONLY_HIGH},
    {"category": HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, "threshold": HarmBlockThreshold.BLOCK_ONLY_HIGH},
    {"category": HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, "threshold": HarmBlockThreshold.BLOCK_ONLY_HIGH},
]

DEFAULT_EXTRACTION: dict[str, Any] = {
    "budget": "",
    "intent": "",
    "competitors": [],
    "product": "",
    "timeline": "",
    "industry": "",
    "custom_fields": {},
}

_CONFIGURED = False

_RETIRED_MODEL_ALIASES: dict[str, str] = {
    "gemini-1.5-flash": "gemini-2.5-flash",
    "gemini-1.5-flash-8b": "gemini-2.5-flash",
    "gemini-1.5-pro": "gemini-2.5-pro",
}


def _resolve_model_name(name: str) -> str:
    key = name.strip().lower()
    if key in _RETIRED_MODEL_ALIASES:
        resolved = _RETIRED_MODEL_ALIASES[key]
        logger.warning(
            "Model %r is no longer available; using %r instead. Update GEMINI_MODEL in .env.",
            name,
            resolved,
        )
        return resolved
    return name.strip()


def _ensure_configured() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    key = settings.gemini_api_key
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not set")
    genai.configure(api_key=key)  # type: ignore[attr-defined]
    _CONFIGURED = True


def extract_text_from_gemini_response(response: Any) -> str:
    """
    Read model output without relying on `response.text` alone (it raises when parts are empty
    or the candidate was filtered — we still want logs and any recoverable text).
    """
    try:
        t = (response.text or "").strip()
        if t:
            return t
    except ValueError as exc:
        logger.warning("Gemini response.text unavailable: %s", exc)

    pf = getattr(response, "prompt_feedback", None)
    if pf is not None:
        br = getattr(pf, "block_reason", None)
        if br is not None and str(br) not in ("0", "BLOCK_REASON_UNSPECIFIED", ""):
            logger.warning("Gemini prompt_feedback block_reason=%s", br)

    chunks: list[str] = []
    for cand in getattr(response, "candidates", None) or []:
        content = getattr(cand, "content", None)
        parts = getattr(content, "parts", None) if content else None
        if not parts:
            fr = getattr(cand, "finish_reason", None)
            logger.warning(
                "Gemini candidate has no parts (finish_reason=%s)",
                fr,
            )
            continue
        for part in parts:
            pt = getattr(part, "text", None)
            if pt:
                chunks.append(pt)
    return "".join(chunks).strip()


def _strip_markdown_fences(raw: str) -> str:
    """Remove common ``` / ```json wrappers if the model still emits them."""
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```\s*$", "", text)
    return text.strip()


def _parse_json_loose(raw: str) -> Any | None:
    """Parse JSON; if the model adds a short preamble, take the outermost `{...}` slice."""
    cleaned = _strip_markdown_fences(raw)
    try:
        return json.loads(cleaned)
    except (json.JSONDecodeError, TypeError, ValueError):
        pass
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(cleaned[start : end + 1])
        except (json.JSONDecodeError, TypeError, ValueError):
            return None
    return None


def _coerce_competitors(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    if isinstance(value, str) and value.strip():
        return [c.strip() for c in re.split(r"[,;]", value) if c.strip()]
    return []


def _coerce_custom_fields(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    out: dict[str, str] = {}
    for i, (k, v) in enumerate(value.items()):
        if i >= 20:
            break
        ks = str(k).strip()
        if not ks:
            continue
        out[ks[:128]] = str(v).strip()[:2048] if v is not None else ""
    return out


def _normalize(data: Any) -> dict[str, Any]:
    out = dict(DEFAULT_EXTRACTION)
    if not isinstance(data, dict):
        return out
    b = data.get("budget")
    if isinstance(b, (int, float)):
        out["budget"] = str(b)
    else:
        out["budget"] = str(b or "").strip()
    out["intent"] = str(data.get("intent") or "").strip()
    out["product"] = str(data.get("product") or "").strip()
    out["timeline"] = str(data.get("timeline") or "").strip()
    out["industry"] = str(data.get("industry") or "").strip()
    out["competitors"] = _coerce_competitors(data.get("competitors"))
    out["custom_fields"] = _coerce_custom_fields(data.get("custom_fields"))
    return out


def execute_gemini_json_extraction(full_prompt: str) -> dict[str, Any]:
    """
    Send `full_prompt` to Gemini and return normalized extraction dict.

    On missing configuration, API errors, or invalid JSON, returns
    `DEFAULT_EXTRACTION` and logs the issue. On JSON parse failure, logs the
    full raw model response.
    """
    if not full_prompt or not full_prompt.strip():
        return dict(DEFAULT_EXTRACTION)

    try:
        _ensure_configured()
    except RuntimeError as exc:
        logger.error("%s", exc)
        return dict(DEFAULT_EXTRACTION)

    raw_name = (settings.gemini_model or "").strip()
    if not raw_name:
        logger.error("GEMINI_MODEL is not set; cannot select a Gemini model")
        return dict(DEFAULT_EXTRACTION)

    model_name = _resolve_model_name(raw_name)

    try:
        model = genai.GenerativeModel(  # type: ignore[attr-defined]
            model_name,
            safety_settings=GEMINI_SAFETY_SETTINGS,
            generation_config=genai.GenerationConfig(  # type: ignore[attr-defined]
                response_mime_type="application/json",
            ),
        )
        response = model.generate_content(full_prompt)
        raw = extract_text_from_gemini_response(response)
    except Exception:
        logger.exception("Gemini request failed for model %s", model_name)
        return dict(DEFAULT_EXTRACTION)

    if not raw:
        logger.warning("Gemini returned empty text")
        return dict(DEFAULT_EXTRACTION)

    parsed = _parse_json_loose(raw)
    if parsed is None:
        logger.warning(
            "Failed to parse Gemini response as JSON; raw response: %s",
            raw[:4000] if raw else "",
        )
        return dict(DEFAULT_EXTRACTION)

    return _normalize(parsed)
