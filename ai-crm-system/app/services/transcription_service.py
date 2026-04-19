"""
Audio transcription using faster-whisper (CTranslate2 backend).

Why faster-whisper (vs openai-whisper):
- 2x to 4x faster decoding on CPU and GPU.
- Lower memory footprint; supports INT8 quantization on CPU.
- No torch / torchaudio dependency.
- Same model family (tiny, base, small, medium, large-v3).

Still requires FFmpeg on PATH for many container formats (mp4, m4a, webm, ...).
"""

from __future__ import annotations

import logging
import os
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

_model: Any = None
_loaded_key: tuple[str, str, str] | None = None

_WHISPER_INSTALL_HINT = (
    "faster-whisper is not installed in this Python environment. Install it with "
    "`pip install -r requirements.txt` (or `pip install faster-whisper`). "
    "Then restart Uvicorn from the project venv, e.g. "
    "`myvenv\\Scripts\\python -m uvicorn app.main:app --reload` on Windows."
)

_FFMPEG_HINT = (
    "FFmpeg is required to decode most audio/video formats. Install FFmpeg and add it "
    "to the system PATH, then restart the API. On Windows: `winget install Gyan.FFmpeg` "
    "or download from https://ffmpeg.org. Verify with `ffmpeg -version` in a new terminal."
)


class WhisperNotInstalledError(RuntimeError):
    """Raised when the `faster_whisper` module is missing."""


class FfmpegRequiredError(RuntimeError):
    """Raised when FFmpeg is not available (needed to decode non-WAV audio)."""


def _detect_device_and_compute() -> tuple[str, str]:
    """
    Pick a sensible (device, compute_type) pair.

    - `WHISPER_DEVICE` override: "cpu", "cuda", or "auto" (default).
    - `WHISPER_COMPUTE_TYPE` override: e.g. "int8", "int8_float16", "float16", "float32".
    - CPU default is `int8` which is the fastest general-purpose setting.
    - GPU default is `float16` when CUDA is available.
    """
    device_cfg = (getattr(settings, "whisper_device", None) or "auto").strip().lower()
    compute_cfg = (getattr(settings, "whisper_compute_type", None) or "").strip().lower()

    device = "cpu"
    if device_cfg in ("cuda", "gpu"):
        device = "cuda"
    elif device_cfg == "auto":
        try:
            from ctranslate2 import get_cuda_device_count  # type: ignore

            if int(get_cuda_device_count()) > 0:
                device = "cuda"
        except Exception:
            device = "cpu"

    if compute_cfg:
        compute_type = compute_cfg
    else:
        compute_type = "float16" if device == "cuda" else "int8"

    return device, compute_type


def _get_whisper_model():
    """Lazy-load faster-whisper model (reloaded if config changes)."""
    global _model, _loaded_key

    name = (settings.whisper_model or "base").strip() or "base"
    device, compute_type = _detect_device_and_compute()
    key = (name, device, compute_type)

    if _model is not None and _loaded_key == key:
        return _model

    try:
        from faster_whisper import WhisperModel
    except ModuleNotFoundError as e:
        raise WhisperNotInstalledError(_WHISPER_INSTALL_HINT) from e

    cpu_threads = int(os.environ.get("WHISPER_CPU_THREADS", "0") or 0)
    num_workers = int(os.environ.get("WHISPER_NUM_WORKERS", "1") or 1)

    logger.info(
        "Loading faster-whisper model name=%r device=%s compute_type=%s threads=%s workers=%s",
        name, device, compute_type, cpu_threads or "auto", num_workers,
    )
    _model = WhisperModel(
        name,
        device=device,
        compute_type=compute_type,
        cpu_threads=cpu_threads,
        num_workers=num_workers,
    )
    _loaded_key = key
    return _model


def _beam_size() -> int:
    if getattr(settings, "whisper_fast_decode", True):
        return 1
    try:
        beam = int(getattr(settings, "whisper_beam_size", 1) or 1)
    except (TypeError, ValueError):
        beam = 1
    return max(1, min(10, beam))


def transcribe_audio(file_path: str) -> str:
    """Transcribe an audio file to plain text."""
    return transcribe_audio_detailed(file_path)["plain_text"]


def _log_prob_threshold() -> float | None:
    raw = str(getattr(settings, "whisper_log_prob_threshold", "") or "").strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _vad_parameters() -> dict | None:
    if not bool(getattr(settings, "whisper_vad", True)):
        return None
    try:
        min_silence = int(getattr(settings, "whisper_vad_min_silence_ms", 500) or 500)
    except (TypeError, ValueError):
        min_silence = 500
    return {"min_silence_duration_ms": max(100, min_silence)}


def transcribe_audio_detailed(file_path: str) -> dict:
    """
    Transcribe with per-segment timestamps.

    Returns {"plain_text": str, "segments": list[dict]} where each segment is
    {"start": float, "end": float, "text": str, "speaker": None}.
    """
    model = _get_whisper_model()
    beam = _beam_size()
    lang = (getattr(settings, "whisper_language", None) or "").strip() or None
    vad = bool(getattr(settings, "whisper_vad", True))
    vad_params = _vad_parameters()
    lp_threshold = _log_prob_threshold()

    kwargs: dict[str, Any] = {
        "beam_size": beam,
        "language": lang,
        "vad_filter": vad,
        "condition_on_previous_text": False,
    }
    if vad_params is not None:
        kwargs["vad_parameters"] = vad_params
    if lp_threshold is not None:
        kwargs["log_prob_threshold"] = lp_threshold

    try:
        segments_iter, _info = model.transcribe(file_path, **kwargs)
    except FileNotFoundError as e:
        raise FfmpegRequiredError(_FFMPEG_HINT) from e
    except RuntimeError as e:
        msg = str(e).lower()
        if "ffmpeg" in msg or "no such file" in msg or "unable to open" in msg:
            raise FfmpegRequiredError(_FFMPEG_HINT) from e
        raise

    segments_out: list[dict] = []
    text_parts: list[str] = []
    for seg in segments_iter:
        txt = (seg.text or "").strip()
        if not txt:
            continue
        try:
            start = float(seg.start)
            end = float(seg.end)
        except (TypeError, ValueError):
            start, end = 0.0, 0.0
        segments_out.append(
            {
                "start": round(start, 2),
                "end": round(end, 2),
                "text": txt,
                "speaker": None,
            }
        )
        text_parts.append(txt)

    text = " ".join(text_parts).strip()
    return {"plain_text": text, "segments": segments_out}
