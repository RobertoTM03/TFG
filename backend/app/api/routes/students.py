from typing import Optional

from fastapi import APIRouter, Depends, Query, Request

from app.api.dependencies import get_current_user
from app.api.schemas import (
    PaginatedResponse,
    StudentOverviewResponse,
    StudentRepoScoreResponse,
    StudentSummaryDetailResponse,
    StudentSummaryResponse,
    TaskSummaryResponse,
)
from app.infrastructure.limiter import limiter, rate_limit_default

router = APIRouter(prefix="/api", tags=["Students"])


@router.get(
    "/repos/{owner}/{repo}/students",
    response_model=list[StudentSummaryResponse],
    summary="List students who have submitted PRs to a repository",
)
@limiter.limit(rate_limit_default)
async def list_repo_students(
    owner: str,
    repo: str,
    request: Request,
    user: dict = Depends(get_current_user),
):
    """Return one entry per student (pr_author) who has opened a PR against
    this repository, with their submission count and the status of their
    most recent evaluation."""
    db = request.app.state.database
    rows = db.get_repo_students(str(user["id"]), f"{owner}/{repo}")
    return [
        StudentSummaryResponse(
            pr_author=r["pr_author"],
            submissions=r["submissions"],
            last_status=r["last_status"],
            last_submitted_at=str(r["last_submitted_at"]) if r.get("last_submitted_at") else None,
            last_task_id=str(r["last_task_id"]) if r.get("last_task_id") else None,
        )
        for r in rows
    ]


@router.get(
    "/students",
    response_model=list[StudentOverviewResponse],
    summary="List all students across all repositories of the professor",
)
@limiter.limit(rate_limit_default)
async def list_all_students(
    request: Request,
    user: dict = Depends(get_current_user),
):
    """Return one entry per student (pr_author) across every repository owned
    by the authenticated professor, including their best score (0–10)."""
    db = request.app.state.database
    rows = db.get_all_students(str(user["id"]))
    return [
        StudentOverviewResponse(
            pr_author=r["pr_author"],
            total_submissions=r["total_submissions"],
            completed_submissions=r["completed_submissions"],
            repo_count=r["repo_count"],
            best_score=float(round(r["best_score"], 2)) if r.get("best_score") is not None else None,
            last_status=r["last_status"],
            last_submitted_at=str(r["last_submitted_at"]) if r.get("last_submitted_at") else None,
            last_task_id=str(r["last_task_id"]) if r.get("last_task_id") else None,
        )
        for r in rows
    ]


@router.get(
    "/students/{github_login}/summary",
    response_model=StudentSummaryDetailResponse,
    summary="Per-repository score breakdown for a student",
)
@limiter.limit(rate_limit_default)
async def get_student_summary(
    github_login: str,
    request: Request,
    user: dict = Depends(get_current_user),
):
    """Return per-repository stats and rule-verdict breakdown for a student,
    computed from all completed evaluation tasks."""
    db = request.app.state.database
    rows = db.get_student_repo_scores(str(user["id"]), github_login)

    repo_scores: list[StudentRepoScoreResponse] = []
    total_submissions = 0
    completed_submissions = 0
    best_overall: Optional[float] = None

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

        best_score = float(round(r["best_score"], 2)) if r.get("best_score") is not None else None
        if best_score is not None and (best_overall is None or best_score > best_overall):
            best_overall = best_score

        repo_scores.append(
            StudentRepoScoreResponse(
                repository_full_name=r["repository_full_name"],
                total_submissions=r["total_submissions"],
                completed_submissions=r["completed_submissions"],
                best_score=best_score,
                best_task_id=str(r["best_task_id"]) if r.get("best_task_id") else None,
                best_pr_number=r.get("best_pr_number"),
                pass_count=pass_count,
                partial_count=partial_count,
                fail_count=fail_count,
                last_submitted_at=str(r["last_submitted_at"]) if r.get("last_submitted_at") else None,
            )
        )

    return StudentSummaryDetailResponse(
        pr_author=github_login,
        best_score_overall=best_overall,
        total_submissions=total_submissions,
        completed_submissions=completed_submissions,
        repos=repo_scores,
    )


@router.get(
    "/students/{github_login}/tasks",
    response_model=PaginatedResponse[TaskSummaryResponse],
    summary="List all evaluations for a student across all repositories",
)
@limiter.limit(rate_limit_default)
async def list_student_tasks(
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
    """Return all evaluation tasks for a given student (GitHub login) scoped
    to the authenticated professor's repositories."""
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
