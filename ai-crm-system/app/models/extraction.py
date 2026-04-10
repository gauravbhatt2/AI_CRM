from pydantic import BaseModel, Field


class ExtractionPreviewResponse(BaseModel):
    """Placeholder response for future AI extraction endpoints."""

    message: str = Field(
        default="Extraction pipeline not implemented yet.",
        description="Human-readable status",
    )
