from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Service health check payload."""

    status: str = Field(..., description="Overall health status")
    version: str = Field(default="0.1.0", description="API version string")
