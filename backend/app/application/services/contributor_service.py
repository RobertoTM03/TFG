from typing import Any, Dict, List, Optional

from app.domain.ports.contributor_repository import ContributorRepositoryPort
from app.domain.ports.task_repository import TaskRepositoryPort


class ContributorService:
    def __init__(
        self,
        contributor_repo: ContributorRepositoryPort,
        task_repo: TaskRepositoryPort,
    ) -> None:
        self._contributor_repo = contributor_repo
        self._task_repo = task_repo

    def get_repo_contributors(
        self, user_id: str, repo_full_name: str,
    ) -> List[Dict[str, Any]]:
        return self._contributor_repo.get_repo_contributors(user_id, repo_full_name)

    def get_all_contributors(self, user_id: str) -> List[Dict[str, Any]]:
        return self._contributor_repo.get_all_contributors(user_id)

    def get_contributor_summary(
        self, user_id: str, github_login: str,
    ) -> Dict[str, Any]:
        rows = self._contributor_repo.get_contributor_repo_stats(user_id, github_login)

        repo_stats: list = []
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

            repo_stats.append({
                "repository_full_name": r["repository_full_name"],
                "total_submissions": r["total_submissions"],
                "completed_submissions": r["completed_submissions"],
                "best_task_id": str(r["best_task_id"]) if r.get("best_task_id") else None,
                "best_pr_number": r.get("best_pr_number"),
                "pass_count": pass_count,
                "partial_count": partial_count,
                "fail_count": fail_count,
                "last_submitted_at": str(r["last_submitted_at"]) if r.get("last_submitted_at") else None,
            })

        return {
            "pr_author": github_login,
            "total_submissions": total_submissions,
            "completed_submissions": completed_submissions,
            "repos": repo_stats,
        }

    def list_contributor_tasks(
        self,
        user_id: str,
        github_login: str,
        page: int = 1,
        page_size: int = 20,
        repository_full_name: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        total = self._task_repo.count_user_tasks(
            user_id,
            repository_full_name=repository_full_name,
            pr_author=github_login,
            status=status,
        )
        rows = self._task_repo.get_user_tasks(
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
        return {"items": rows, "total": total, "page": page, "page_size": page_size, "total_pages": total_pages}
