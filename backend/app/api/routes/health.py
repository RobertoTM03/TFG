from fastapi import APIRouter, Request

from app.api.schemas import HealthResponse, RepomapRequest, RepomapResponse
from app.application.services.health_service import HealthService
from app.application.services.repomap_service import RepomapService

router = APIRouter(tags=["Health"])


@router.get("/", summary="Health check", response_model=HealthResponse)
async def health_check(request: Request):
    """Return the health status of every system component."""
    service = HealthService(request.app.state.container)
    return service.check()


@router.post(
    "/repomap",
    summary="Generate repository map (synchronous)",
    response_model=RepomapResponse,
)
async def generate_repomap(body: RepomapRequest, request: Request):
    """Clone the repository and return its tree-sitter based repomap."""
    service = RepomapService(request.app.state.container)
    repomap = service.generate_repomap(body.repository_url)
    return RepomapResponse(repository_url=body.repository_url, repomap=repomap)
