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


def _role_from_label(label: str) -> str | None:
    s = (label or "").strip().lower()
    if not s:
        return None
    if "sales" in s or s in {"rep", "agent"}:
        return "Sales"
    if "customer" in s or s in {"prospect", "buyer", "client"}:
        return "Customer"
    return None


def _render_label(role: str, sales_name: str, customer_name: str) -> str:
    if role == "Sales":
        return f"{sales_name} (Sales)" if sales_name else "Sales"
    return f"{customer_name} (Customer)" if customer_name else "Customer"


def _extract_names_from_text(text: str) -> tuple[str, str]:
    """Best-effort sales/customer name discovery from transcript text."""
    def _clean_name(v: str) -> str:
        s = (v or "").strip()
        s = re.sub(r"\bfrom\s*$", "", s, flags=re.I).strip()
        parts = [p for p in s.split() if p]
        if len(parts) > 2:
            parts = parts[:2]
        return " ".join(parts)

    sales_name = ""
    customer_name = ""
    names = re.findall(
        r"\b(?:my name is|this is)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
        text,
        flags=re.I,
    )
    if names:
        if re.search(r"thank you for calling", text, flags=re.I):
            sales_name = _clean_name(names[0])
            if len(names) > 1:
                customer_name = _clean_name(names[1])
        else:
            customer_name = _clean_name(names[0])
            if len(names) > 1:
                sales_name = _clean_name(names[1])
    # Explicit "from <Company>" line usually belongs to the customer intro turn.
    if not customer_name:
        m = re.search(r"\bthis is\s+([A-Z][a-z]+)\s+from\s+[A-Z]", text, flags=re.I)
        if m:
            customer_name = _clean_name(m.group(1))
    return sales_name, customer_name


def _repair_speaker_turns(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Repair obvious speaker assignment errors using dialogue cues.

    Handles common ASR cases where one segment is mislabeled in an otherwise good sequence.
    """
    if not segments:
        return segments

    combined = " ".join(str(s.get("text") or "") for s in segments)
    sales_name, customer_name = _extract_names_from_text(combined)

    # Prefer names already present in labels.
    for seg in segments:
        sp = str(seg.get("speaker") or "")
        m_sales = re.search(r"^(.+?)\s*\(sales\)\s*$", sp, flags=re.I)
        m_cust = re.search(r"^(.+?)\s*\(customer\)\s*$", sp, flags=re.I)
        if m_sales and not sales_name:
            sales_name = m_sales.group(1).strip()
        if m_cust and not customer_name:
            customer_name = m_cust.group(1).strip()

    sales_cues = (
        "thank you for calling",
        "how can i help",
        "i'd be happy to help",
        "did you receive",
        "verify your address",
        "located your information",
        "newest version",
        "price of",
        "set up this order",
        "ship out today",
        "credit card",
        "recommend taking advantage",
    )
    customer_cues = (
        "i was just calling",
        "i have a",
        "my phone number",
        "my name is",
        "this is ",
        "from ",
        "not really sure if i can afford",
        "let's go ahead",
        "use a visa",
        "yes, it's",
        "yeah,",
    )

    repaired: list[dict[str, Any]] = []
    prev_role = "Customer"
    prev_text = ""
    for seg in segments:
        row = dict(seg)
        txt = str(row.get("text") or "").strip()
        low = txt.lower()
        role = _role_from_label(str(row.get("speaker") or "")) or prev_role

        # Strong lexical cues.
        if any(k in low for k in sales_cues):
            role = "Sales"
        elif any(k in low for k in customer_cues):
            role = "Customer"
        # "This is <Name>" without service phrasing is usually a customer intro.
        if re.search(r"\bthis is\s+[A-Z][a-z]+", txt) and "thank you for calling" not in low:
            role = "Customer"

        # If previous turn was a question from Sales, short confirmation likely Customer.
        if (
            prev_role == "Sales"
            and "?" in prev_text
            and re.match(r"^(yes|yeah|yep|no|nope|it'?s|my|i do|i did)\b", low)
        ):
            role = "Customer"

        # If current line asks for verification/order details, usually Sales.
        if "?" in low and any(k in low for k in ("can i have", "do you have", "would you", "please")):
            role = "Sales"

        row["speaker"] = _render_label(role, sales_name, customer_name)
        repaired.append(row)
        prev_role = role
        prev_text = txt
    return repaired


def _heuristic_label_segments(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Lightweight fallback when LLM labeling fails.

    This does not perform true diarization; it provides stable role labels so
    downstream transcript rendering still shows "who said what" format.
    """
    combined = " ".join(str(s.get("text") or "") for s in segments)
    sales_name = ""
    customer_name = ""
    # Capture common "my name is X" introductions.
    names = re.findall(r"\bmy name is\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", combined, flags=re.I)
    if names:
        # Heuristic: first intro near "thank you for calling" is often the agent.
        if re.search(r"thank you for calling", combined, flags=re.I):
            sales_name = names[0].strip()
            if len(names) > 1:
                customer_name = names[1].strip()
        else:
            customer_name = names[0].strip()

    out: list[dict[str, Any]] = []
    last_role = "Customer"
    for seg in segments:
        row = dict(seg)
        txt = str(row.get("text") or "").lower()
        sales_cues = (
            "thank you for calling",
            "how can i help",
            "i'd be happy to help",
            "did you receive",
            "verify your address",
            "located your information",
            "newest version",
            "price of",
            "set up this order",
            "recommend",
            "ship out today",
            "credit card",
        )
        customer_cues = (
            "i was just calling",
            "i have a",
            "my phone number",
            "my name is",
            "not really sure if i can afford",
            "let's go ahead",
            "use a visa",
        )
        role = last_role
        if any(k in txt for k in sales_cues):
            role = "Sales"
        elif any(k in txt for k in customer_cues):
            role = "Customer"
        elif "?" in txt:
            # Alternate on unknown question turns to avoid one-label collapse.
            role = "Sales" if last_role == "Customer" else "Customer"

        if role == "Sales" and sales_name:
            row["speaker"] = f"{sales_name} (Sales)"
        elif role == "Customer" and customer_name:
            row["speaker"] = f"{customer_name} (Customer)"
        else:
            row["speaker"] = role
        last_role = role
        out.append(row)
    return _repair_speaker_turns(out)


def heuristic_speaker_segments(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Rule-based speaker labels without Groq (Sales/Customer heuristics)."""
    return _heuristic_label_segments(segments)


def maybe_relabel_speakers_ab(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Map distinct speaker labels to Speaker A / Speaker B (first two unique speakers in order).
    Collapses additional speakers onto Speaker B. No-op unless settings.transcript_speaker_labels == "speaker_ab".
    """
    if getattr(settings, "transcript_speaker_labels", "roles") != "speaker_ab":
        return segments
    if not segments:
        return segments
    mapping: dict[str, str] = {}
    labels = ("Speaker A", "Speaker B")
    next_idx = 0
    out: list[dict[str, Any]] = []
    for seg in segments:
        row = dict(seg)
        raw = str(row.get("speaker") or "").strip() or "__empty__"
        if raw not in mapping:
            if next_idx < 2:
                mapping[raw] = labels[next_idx]
                next_idx += 1
            else:
                mapping[raw] = "Speaker B"
        row["speaker"] = mapping[raw]
        out.append(row)
    return out


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
        return _heuristic_label_segments(segments)

    if not (settings.groq_model or "").strip():
        return _heuristic_label_segments(segments)

    prompt = f"""Label speakers for call transcript segments.

Task:
- For each input segment, set "speaker" to a short consistent label.
- Prefer role labels: "Sales" and "Customer".
- Use a first name only when explicitly stated or unmistakably self-identified.
- Keep the same label for the same person across all segments.
- Keep timestamps exactly as provided for each segment.

Rules:
- Preserve segment order and count exactly.
- Do not merge, split, or rewrite segment text.
- If uncertain, default to "Customer" unless clear seller behavior exists.
- Output must include start/end/text from input with added speaker labels.
- Preserve numeric `start` and `end` values exactly from input.

Return ONLY strict JSON in this shape:
{{"segments": [{{"start": number, "end": number, "text": string, "speaker": string}}]}}

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
        return _heuristic_label_segments(segments)
    except Exception:
        logger.exception("Groq speaker labeling failed")
        return _heuristic_label_segments(segments)

    if not raw:
        return _heuristic_label_segments(segments)
    try:
        parsed = json.loads(_strip_markdown_fences(raw))
    except (json.JSONDecodeError, TypeError, ValueError):
        logger.warning("Speaker JSON parse failed")
        return _heuristic_label_segments(segments)

    labeled = parsed.get("segments") if isinstance(parsed, dict) else None
    if not isinstance(labeled, list) or len(labeled) != len(trimmed):
        return _heuristic_label_segments(segments)

    out: list[dict[str, Any]] = []
    for i, orig in enumerate(trimmed):
        row = dict(orig)
        item = labeled[i]
        if isinstance(item, dict):
            sp = item.get("speaker")
            if isinstance(sp, str) and sp.strip():
                row["speaker"] = sp.strip()[:128]
        out.append(row)
    non_empty = [str(r.get("speaker") or "").strip() for r in out if str(r.get("speaker") or "").strip()]
    unique = {s.lower() for s in non_empty}
    if len(unique) <= 1:
        out = _heuristic_label_segments(trimmed)
    out = _repair_speaker_turns(out)
    if len(segments) > _MAX_SEGMENTS:
        for extra in segments[_MAX_SEGMENTS:]:
            extra_row = dict(extra)
            if not str(extra_row.get("speaker") or "").strip():
                extra_row["speaker"] = "Customer"
            out.append(extra_row)
    return out
