"""Service layer — lazy exports avoid importing mapping/HubSpot when unused."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__all__ = ["ExtractionService", "MappingService"]


def __getattr__(name: str) -> Any:
    if name == "ExtractionService":
        from app.services.extraction_service import ExtractionService

        return ExtractionService
    if name == "MappingService":
        from app.services.mapping_service import MappingService

        return MappingService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


if TYPE_CHECKING:
    from app.services.extraction_service import ExtractionService
    from app.services.mapping_service import MappingService
