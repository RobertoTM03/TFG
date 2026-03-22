from fastapi import APIRouter, Request

from app.api.schemas import HealthResponse
from app.application.services.health_service import HealthService

router = APIRouter(tags=["Health"])


@router.get("/", summary="Health check", response_model=HealthResponse)
async def health_check(request: Request):
    """Return the health status of every system component."""
    service = HealthService(request.app.state.container)
    return service.check()
