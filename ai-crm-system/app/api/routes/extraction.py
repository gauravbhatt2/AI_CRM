from fastapi import APIRouter

from app.models.extraction import ExtractionPreviewResponse
from app.services.extraction_service import ExtractionService

router = APIRouter(prefix="/extraction", tags=["extraction"])

_service = ExtractionService()


@router.get("/preview", response_model=ExtractionPreviewResponse)
async def extraction_preview() -> ExtractionPreviewResponse:
    """Placeholder for a future dry-run extraction endpoint (optional query body later)."""
    _ = _service  # reserved when preview accepts transcript text
    return ExtractionPreviewResponse()
