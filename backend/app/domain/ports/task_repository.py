from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class TaskRepositoryPort(ABC):
    @abstractmethod
    def create_task(
        self,
        repository_url: str,
        repository_full_name: str,
        rules: List[str],
        user_id: Optional[str] = None,
        enable_cross_check: bool = False,
        pr_number: Optional[int] = None,
        pr_head_sha: Optional[str] = None,
        pr_head_ref: Optional[str] = None,
        pr_author: Optional[str] = None,
        github_installation_id: Optional[int] = None,
    ) -> Dict[str, Any]: ...

    @abstractmethod
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]: ...

    @abstractmethod
    def can_view_task(self, task_id: str, user_id: str) -> bool: ...

    @abstractmethod
    def count_user_tasks(
        self,
        user_id: str,
        repository_full_name: Optional[str] = None,
        pr_author: Optional[str] = None,
        status: Optional[str] = None,
    ) -> int: ...

    @abstractmethod
    def get_user_tasks(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        repository_full_name: Optional[str] = None,
        pr_author: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]: ...

    @abstractmethod
    def claim_pending_task(self) -> Optional[Dict[str, Any]]: ...

    @abstractmethod
    def requeue_task(self, task_id: str, delay_seconds: int) -> None: ...

    @abstractmethod
    def update_task_progress(self, task_id: str, progress: int, message: str) -> None: ...

    @abstractmethod
    def save_task_partial_result(self, task_id: str, partial: list) -> None: ...

    @abstractmethod
    def get_task_partial_result(self, task_id: str) -> list: ...

    @abstractmethod
    def complete_task(self, task_id: str, result: dict) -> None: ...

    @abstractmethod
    def fail_task(self, task_id: str, error: str) -> None: ...

    @abstractmethod
    def count_pr_tasks(self, repo_full_name: str, pr_number: int) -> int: ...
