from typing import Optional

from fastapi import APIRouter, Depends, Query, Request

from app.api.dependencies import get_current_user
from app.api.schemas import (
    ContributorDetailResponse,
    ContributorOverviewResponse,
    ContributorRepoStatsResponse,
    ContributorSummaryResponse,
    PaginatedResponse,
    TaskSummaryResponse,
)
from app.infrastructure.limiter import limiter, rate_limit_default

router = APIRouter(prefix="/api", tags=["Contributors"])


@router.get(
    "/repos/{owner}/{repo}/contributors",
    response_model=list[ContributorSummaryResponse],
    summary="List contributors who have submitted PRs to a repository",
)
@limiter.limit(rate_limit_default)
async def list_repo_contributors(
    owner: str,
    repo: str,
    request: Request,
    user: dict = Depends(get_current_user),
):
    service = request.app.state.container.contributor_service
    rows = service.get_repo_contributors(str(user["id"]), f"{owner}/{repo}")
    return [
        ContributorSummaryResponse(
            pr_author=r["pr_author"],
            submissions=r["submissions"],
            last_status=r["last_status"],
            last_submitted_at=str(r["last_submitted_at"]) if r.get("last_submitted_at") else None,
            last_task_id=str(r["last_task_id"]) if r.get("last_task_id") else None,
        )
        for r in rows
    ]


@router.get(
    "/contributors",
    response_model=list[ContributorOverviewResponse],
    summary="List all contributors across all repositories",
)
@limiter.limit(rate_limit_default)
async def list_all_contributors(
    request: Request,
    user: dict = Depends(get_current_user),
):
    service = request.app.state.container.contributor_service
    rows = service.get_all_contributors(str(user["id"]))
    return [
        ContributorOverviewResponse(
            pr_author=r["pr_author"],
            total_submissions=r["total_submissions"],
            completed_submissions=r["completed_submissions"],
            repo_count=r["repo_count"],
            last_status=r["last_status"],
            last_submitted_at=str(r["last_submitted_at"]) if r.get("last_submitted_at") else None,
            last_task_id=str(r["last_task_id"]) if r.get("last_task_id") else None,
        )
        for r in rows
    ]


@router.get(
    "/contributors/{github_login}/summary",
    response_model=ContributorDetailResponse,
    summary="Per-repository rule-verdict breakdown for a contributor",
)
@limiter.limit(rate_limit_default)
async def get_contributor_summary(
    github_login: str,
    request: Request,
    user: dict = Depends(get_current_user),
):
    service = request.app.state.container.contributor_service
    data = service.get_contributor_summary(str(user["id"]), github_login)

    return ContributorDetailResponse(
        pr_author=data["pr_author"],
        total_submissions=data["total_submissions"],
        completed_submissions=data["completed_submissions"],
        repos=[
            ContributorRepoStatsResponse(**repo)
            for repo in data["repos"]
        ],
    )


@router.get(
    "/contributors/{github_login}/tasks",
    response_model=PaginatedResponse[TaskSummaryResponse],
    summary="List all evaluations for a contributor across all repositories",
)
@limiter.limit(rate_limit_default)
async def list_contributor_tasks(
    github_login: str,
    request: Request,
    user: dict = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    repository_full_name: Optional[str] = Query(
        None, description="Filter by repository (e.g. owner/repo)"
    ),
    status: Optional[str] = Query(
        None, description="Filter by task status (pending, running, completed, failed)"
    ),
):
    service = request.app.state.container.contributor_service
    result = service.list_contributor_tasks(
        user_id=str(user["id"]),
        github_login=github_login,
        page=page,
        page_size=page_size,
        repository_full_name=repository_full_name,
        status=status,
    )

    return PaginatedResponse[TaskSummaryResponse](
        items=[
            TaskSummaryResponse(
                id=str(t["id"]),
                repository_full_name=t["repository_full_name"],
                status=t["status"],
                progress=t.get("progress", 0),
                progress_message=t.get("progress_message", ""),
                created_at=str(t["created_at"]),
                completed_at=str(t["completed_at"]) if t.get("completed_at") else None,
                pr_number=t.get("pr_number"),
                pr_author=t.get("pr_author"),
            )
            for t in result["items"]
        ],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
        total_pages=result["total_pages"],
    )
