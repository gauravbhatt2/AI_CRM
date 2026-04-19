"""
Speaker diarization via pyannote.audio (optional). Maps up to two speakers to Speaker A / Speaker B.

Requires HUGGINGFACE_TOKEN and accepted model license on Hugging Face.
Falls back silently if pyannote/torch unavailable or diarization fails.
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

# Default community pipeline (requires HF token + license acceptance)
DEFAULT_DIARIZATION_MODEL = "pyannote/speaker-diarization-3.1"

_pipeline_cache: Any = None
_pipeline_model_id: str | None = None


def _load_pipeline():
    """Lazy-load pyannote pipeline once per process (reload if model id changes)."""
    global _pipeline_cache, _pipeline_model_id
    token = (getattr(settings, "huggingface_token", None) or "").strip()
    if not token:
        return None
    model_id = (getattr(settings, "pyannote_model_id", None) or DEFAULT_DIARIZATION_MODEL).strip()
    if _pipeline_cache is not None and _pipeline_model_id == model_id:
        return _pipeline_cache
    try:
        from pyannote.audio import Pipeline
    except ImportError as e:
        logger.warning("pyannote.audio not installed: %s", e)
        return None
    try:
        try:
            pipeline = Pipeline.from_pretrained(model_id, token=token)
        except TypeError:
            pipeline = Pipeline.from_pretrained(model_id, use_auth_token=token)
        _pipeline_cache = pipeline
        _pipeline_model_id = model_id
        return pipeline
    except Exception as exc:
        logger.warning("Could not load pyannote pipeline %s: %s", model_id, exc)
        return None


def run_diarization_turns(audio_path: str) -> list[tuple[float, float, str]]:
    """
    Return list of (start_sec, end_sec, raw_label) for each speech turn.
    Empty list if unavailable or on error.
    """
    pipeline = _load_pipeline()
    if pipeline is None:
        return []
    try:
        diar = pipeline({"audio": audio_path})
    except Exception as exc:
        logger.warning("pyannote diarization failed: %s", exc)
        return []

    turns: list[tuple[float, float, str]] = []
    try:
        for segment, _track, label in diar.itertracks(yield_label=True):
            turns.append((float(segment.start), float(segment.end), str(label)))
    except Exception as exc:
        logger.warning("Could not iterate pyannote output: %s", exc)
        return []

    turns.sort(key=lambda x: x[0])
    return turns


def _build_ab_mapping(raw_labels: list[str]) -> dict[str, str]:
    """Map pyannote labels to Speaker A / Speaker B (first two unique speakers)."""
    order: list[str] = []
    seen: set[str] = set()
    for lab in raw_labels:
        if lab not in seen:
            seen.add(lab)
            order.append(lab)
    mapping: dict[str, str] = {}
    if len(order) >= 1:
        mapping[order[0]] = "Speaker A"
    if len(order) >= 2:
        mapping[order[1]] = "Speaker B"
    for extra in order[2:]:
        mapping[extra] = "Speaker B"
    return mapping


def _overlap(a0: float, a1: float, b0: float, b1: float) -> float:
    return max(0.0, min(a1, b1) - max(a0, b0))


def merge_diarization_with_whisper_segments(
    segments: list[dict[str, Any]],
    turns: list[tuple[float, float, str]],
) -> list[dict[str, Any]]:
    """
    Assign Speaker A/B to each Whisper segment using timestamp overlap with diarization turns.
    """
    if not segments or not turns:
        return [dict(s) for s in segments]

    raw_order = [t[2] for t in turns]
    ab = _build_ab_mapping(raw_order)

    out: list[dict[str, Any]] = []
    for seg in segments:
        row = dict(seg)
        try:
            s0 = float(seg.get("start", 0.0))
            s1 = float(seg.get("end", 0.0))
        except (TypeError, ValueError):
            s0, s1 = 0.0, 0.0
        if s1 < s0:
            s0, s1 = s1, s0

        best_lab: str | None = None
        best_ov = 0.0
        for t0, t1, lab in turns:
            ov = _overlap(s0, s1, t0, t1)
            if ov > best_ov:
                best_ov = ov
                best_lab = lab

        if best_lab is None or best_ov <= 0:
            mid = 0.5 * (s0 + s1)
            for t0, t1, lab in turns:
                if t0 <= mid <= t1:
                    best_lab = lab
                    break

        sp = ab.get(best_lab, "Speaker A") if best_lab else None
        row["speaker"] = sp
        out.append(row)
    return out


def apply_pyannote_to_segments(audio_path: str, segments: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    """
    Run diarization and merge with Whisper segments. Returns (segments, applied_flag).
    """
    if not getattr(settings, "pyannote_enabled", True):
        return [dict(s) for s in segments], False
    if not (getattr(settings, "huggingface_token", None) or "").strip():
        return [dict(s) for s in segments], False
    turns = run_diarization_turns(audio_path)
    if not turns:
        return [dict(s) for s in segments], False
    merged = merge_diarization_with_whisper_segments(segments, turns)
    return merged, True
