from fastapi import APIRouter, Request

from app.api.schemas import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/", summary="Health check", response_model=HealthResponse)
async def health_check(request: Request):
    """Return the health status of every system component."""
    return request.app.state.container.health_service.check()
