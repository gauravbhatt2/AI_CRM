"""
Map extracted structures to CRM entities — uses `MappingService` internally.

Add entity-specific rules (contact vs deal) and conflict resolution here.
"""

from typing import Any

from app.services.mapping_service import MappingService


class CRMMappingEngine:
    """Coordinates mapping from extraction output to CRM records."""

    def __init__(self, service: MappingService | None = None) -> None:
        self._service = service or MappingService()

    def apply(self, extracted: dict[str, Any]) -> dict[str, Any]:
        """Placeholder mapping pass."""
        return self._service.map_to_crm(extracted)
