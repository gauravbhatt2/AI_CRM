"""
AI extraction pipeline — orchestrates calls into `ExtractionService`.

Add LLM prompts, parsers, and validation here.
"""

from typing import Any

from app.services.extraction_service import ExtractionService


class ExtractionPipeline:
    """Thin orchestrator over extraction business logic."""

    def __init__(self, service: ExtractionService | None = None) -> None:
        self._service = service or ExtractionService()

    def run(self, text: str, **kwargs: Any) -> dict[str, Any]:
        """Placeholder pipeline step."""
        ctx = kwargs if kwargs else None
        return self._service.extract_entities(text, context=ctx)
