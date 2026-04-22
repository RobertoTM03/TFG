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
    """Return one entry per contributor (pr_author) who has opened a PR against
    this repository, with their submission count and most recent evaluation status."""
    db = request.app.state.database
    rows = db.get_repo_contributors(str(user["id"]), f"{owner}/{repo}")
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
    """Return one entry per contributor (pr_author) across every repository owned
    by the authenticated user."""
    db = request.app.state.database
    rows = db.get_all_contributors(str(user["id"]))
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
    """Return per-repository stats and rule-verdict counts for a contributor,
    derived from their most recent completed evaluation per repository."""
    db = request.app.state.database
    rows = db.get_contributor_repo_stats(str(user["id"]), github_login)

    repo_stats: list[ContributorRepoStatsResponse] = []
    total_submissions = 0
    completed_submissions = 0

    for r in rows:
        total_submissions += r["total_submissions"]
        completed_submissions += r["completed_submissions"]

        pass_count = partial_count = fail_count = 0
        best_result = r.get("best_result")
        if best_result and isinstance(best_result, dict):
            for v in best_result.get("validations", []):
                verdict = (v.get("evaluation") or {}).get("verdict", "fail")
                if verdict == "pass":
                    pass_count += 1
                elif verdict == "partial":
                    partial_count += 1
                else:
                    fail_count += 1

        repo_stats.append(
            ContributorRepoStatsResponse(
                repository_full_name=r["repository_full_name"],
                total_submissions=r["total_submissions"],
                completed_submissions=r["completed_submissions"],
                best_task_id=str(r["best_task_id"]) if r.get("best_task_id") else None,
                best_pr_number=r.get("best_pr_number"),
                pass_count=pass_count,
                partial_count=partial_count,
                fail_count=fail_count,
                last_submitted_at=str(r["last_submitted_at"]) if r.get("last_submitted_at") else None,
            )
        )

    return ContributorDetailResponse(
        pr_author=github_login,
        total_submissions=total_submissions,
        completed_submissions=completed_submissions,
        repos=repo_stats,
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
    """Return all evaluation tasks for a given contributor (GitHub login) scoped
    to the authenticated user's repositories."""
    db = request.app.state.database
    user_id = str(user["id"])

    total = db.count_user_tasks(
        user_id,
        repository_full_name=repository_full_name,
        pr_author=github_login,
        status=status,
    )
    rows = db.get_user_tasks(
        user_id,
        page=page,
        page_size=page_size,
        sort_by="created_at",
        sort_order="desc",
        repository_full_name=repository_full_name,
        pr_author=github_login,
        status=status,
    )

    total_pages = max(1, -(-total // page_size))
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
            for t in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )
