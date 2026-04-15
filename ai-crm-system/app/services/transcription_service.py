"""
OpenAI Whisper transcription (local model).

Requires FFmpeg on PATH for many audio formats. See: https://github.com/openai/whisper
"""

from __future__ import annotations

import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

_model = None
_loaded_model_name: str | None = None

_WHISPER_INSTALL_HINT = (
    "Install the Whisper package in the same environment as the API: "
    "`pip install openai-whisper` (or `pip install -r requirements.txt`). "
    "Start Uvicorn with the project venv, e.g. "
    "`myvenv\\Scripts\\python -m uvicorn app.main:app --reload` on Windows."
)


class WhisperNotInstalledError(RuntimeError):
    """Raised when the `whisper` module is missing (broken or incomplete install)."""


class FfmpegRequiredError(RuntimeError):
    """Raised when FFmpeg is not available on PATH (Whisper uses it to decode most audio)."""


_FFMPEG_HINT = (
    "FFmpeg is required for Whisper to decode audio (e.g. MP3). Install FFmpeg and add it "
    "to your system PATH, then restart the API. On Windows: `winget install Gyan.FFmpeg` "
    "or `winget install ffmpeg`, or download from https://ffmpeg.org. "
    "Verify with `ffmpeg -version` in a new terminal."
)


def _get_whisper_model():
    """Lazy-load Whisper model once per process (name from settings)."""
    global _model, _loaded_model_name
    name = (settings.whisper_model or "base").strip() or "base"
    if _model is None or _loaded_model_name != name:
        try:
            import whisper
        except ModuleNotFoundError as e:
            raise WhisperNotInstalledError(_WHISPER_INSTALL_HINT) from e

        logger.info("Loading Whisper model %r", name)
        _model = whisper.load_model(name)
        _loaded_model_name = name
    return _model


def transcribe_audio(file_path: str) -> str:
    """
    Transcribe an audio file to plain text using Whisper.

    :param file_path: Path to a readable audio file (wav, mp3, m4a, etc.).
    :return: Transcribed text (stripped). Empty string if nothing decoded.
    """
    return transcribe_audio_detailed(file_path)["plain_text"]


def transcribe_audio_detailed(file_path: str) -> dict:
    """
    Transcribe with per-segment timestamps (Whisper segments).

    Speaker labels are not added here; use `label_segment_speakers` after Groq (optional).
    """
    model = _get_whisper_model()
    try:
        result = model.transcribe(file_path)
    except FileNotFoundError as e:
        # Whisper loads audio via FFmpeg; missing ffmpeg on PATH surfaces as WinError 2 / ENOENT.
        raise FfmpegRequiredError(_FFMPEG_HINT) from e
    text = (result.get("text") or "").strip()
    segments_out: list[dict] = []
    for seg in result.get("segments") or []:
        if not isinstance(seg, dict):
            continue
        try:
            start = float(seg.get("start", 0.0))
            end = float(seg.get("end", 0.0))
        except (TypeError, ValueError):
            start, end = 0.0, 0.0
        st = (seg.get("text") or "").strip()
        if not st:
            continue
        segments_out.append(
            {
                "start": round(start, 2),
                "end": round(end, 2),
                "text": st,
                "speaker": None,
            }
        )
    if not text and segments_out:
        # Whisper sometimes returns empty top-level "text" while segments are present.
        # Downstream extraction expects a non-empty transcript string.
        text = " ".join(s.get("text", "") for s in segments_out).strip()
    return {"plain_text": text, "segments": segments_out}
