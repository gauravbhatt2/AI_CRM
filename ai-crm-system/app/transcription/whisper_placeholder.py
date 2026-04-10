"""
Audio → text transcription — placeholder for OpenAI Whisper or compatible STT.

Wire model loading and inference here when audio ingestion is enabled.
"""

from pathlib import Path
from typing import BinaryIO


class WhisperTranscriptionService:
    """Stub interface matching a future Whisper-backed implementation."""

    def transcribe_file(self, path: Path, language: str | None = None) -> str:
        """Placeholder: returns empty string until Whisper is integrated."""
        _ = path, language
        return ""

    def transcribe_bytes(self, data: BinaryIO, filename: str | None = None) -> str:
        """Placeholder for in-memory audio upload handling."""
        _ = data, filename
        return ""
