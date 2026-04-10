from pydantic import BaseModel, Field


class CRMMapRequest(BaseModel):
    """Placeholder: structured data to map into CRM entities."""

    payload: dict[str, object] = Field(
        default_factory=dict,
        description="Arbitrary extracted fields for mapping",
    )


class CRMMapResponse(BaseModel):
    """Placeholder: result of CRM mapping operation."""

    mapped: bool = Field(default=False, description="Whether mapping was applied")
    detail: str = Field(
        default="CRM mapping not implemented yet.",
        description="Status message",
    )
