from fastapi import APIRouter, Depends, Request

from app.api.dependencies import get_current_user
from app.api.schemas import RepoConfigRequest, RepoConfigResponse

router = APIRouter(prefix="/api/repos", tags=["Repo Config"])

# Default values returned when no config row exists yet
_DEFAULTS = {
    "max_evaluations_per_pr": 3,
    "approval_threshold": 0.8,
    "enable_cross_check": True,
    "pr_evaluation_enabled": True,
}


@router.get(
    "/{owner}/{repo}/config",
    response_model=RepoConfigResponse,
    summary="Get per-repository configuration",
)
async def get_repo_config(
    owner: str,
    repo: str,
    request: Request,
    user: dict = Depends(get_current_user),
):
    full_name = f"{owner}/{repo}"
    db = request.app.state.database
    row = db.get_repo_config(str(user["id"]), full_name)
    if row is None:
        return RepoConfigResponse(**_DEFAULTS)
    return RepoConfigResponse(
        max_evaluations_per_pr=row["max_evaluations_per_pr"],
        approval_threshold=row["approval_threshold"],
        enable_cross_check=row["enable_cross_check"],
        pr_evaluation_enabled=row["pr_evaluation_enabled"],
    )


@router.put(
    "/{owner}/{repo}/config",
    response_model=RepoConfigResponse,
    summary="Create or update per-repository configuration",
)
async def put_repo_config(
    owner: str,
    repo: str,
    body: RepoConfigRequest,
    request: Request,
    user: dict = Depends(get_current_user),
):
    full_name = f"{owner}/{repo}"
    db = request.app.state.database
    row = db.upsert_repo_config(
        user_id=str(user["id"]),
        repo_full_name=full_name,
        max_evaluations_per_pr=body.max_evaluations_per_pr,
        approval_threshold=body.approval_threshold,
        enable_cross_check=body.enable_cross_check,
        pr_evaluation_enabled=body.pr_evaluation_enabled,
    )
    return RepoConfigResponse(
        max_evaluations_per_pr=row["max_evaluations_per_pr"],
        approval_threshold=row["approval_threshold"],
        enable_cross_check=row["enable_cross_check"],
        pr_evaluation_enabled=row["pr_evaluation_enabled"],
    )
