from fastapi import APIRouter

from app.models.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Liveness/readiness probe for load balancers and orchestrators."""
    return HealthResponse(status="ok")
