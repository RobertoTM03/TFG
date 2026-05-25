from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.dependencies import get_current_user
from app.api.schemas import RepoConfigRequest, RepoConfigResponse
from app.config import _VALID_LLM_MODELS

router = APIRouter(prefix="/api/repos", tags=["Repo Config"])

# Default values returned when no config row exists yet
_DEFAULTS = {
    "max_evaluations_per_pr": 3,
    "approval_threshold": 0.8,
    "enable_cross_check": True,
    "pr_evaluation_enabled": True,
    "max_chunks_per_rule": 5,
    "llm_model": None,
    "llm_primary_model": None,
    "llm_secondary_model": None,
}


def _validate_llm_fields(body: RepoConfigRequest) -> None:
    for field, value in [
        ("llm_model", body.llm_model),
        ("llm_primary_model", body.llm_primary_model),
        ("llm_secondary_model", body.llm_secondary_model),
    ]:
        if value is not None and value not in _VALID_LLM_MODELS:
            raise HTTPException(
                status_code=422,
                detail=f"{field}='{value}' is not valid. Choose one of: {sorted(_VALID_LLM_MODELS)}",
            )


def _row_to_response(row: dict) -> RepoConfigResponse:
    return RepoConfigResponse(
        max_evaluations_per_pr=row["max_evaluations_per_pr"],
        approval_threshold=row["approval_threshold"],
        enable_cross_check=row["enable_cross_check"],
        pr_evaluation_enabled=row["pr_evaluation_enabled"],
        max_chunks_per_rule=row["max_chunks_per_rule"],
        llm_model=row.get("llm_model"),
        llm_primary_model=row.get("llm_primary_model"),
        llm_secondary_model=row.get("llm_secondary_model"),
    )


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
    db = request.app.state.repo_config_repo
    row = db.get_repo_config(str(user["id"]), full_name)
    if row is None:
        return RepoConfigResponse(**_DEFAULTS)
    return _row_to_response(row)


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
    _validate_llm_fields(body)
    full_name = f"{owner}/{repo}"
    db = request.app.state.repo_config_repo
    row = db.upsert_repo_config(
        user_id=str(user["id"]),
        repo_full_name=full_name,
        max_evaluations_per_pr=body.max_evaluations_per_pr,
        approval_threshold=body.approval_threshold,
        enable_cross_check=body.enable_cross_check,
        pr_evaluation_enabled=body.pr_evaluation_enabled,
        max_chunks_per_rule=body.max_chunks_per_rule,
        llm_model=body.llm_model,
        llm_primary_model=body.llm_primary_model,
        llm_secondary_model=body.llm_secondary_model,
    )
    return _row_to_response(row)
