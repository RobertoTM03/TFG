from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class RepoConfigRepositoryPort(ABC):
    @abstractmethod
    def get_repo_config(
        self, user_id: str, repo_full_name: str,
    ) -> Optional[Dict[str, Any]]: ...

    @abstractmethod
    def upsert_repo_config(
        self,
        user_id: str,
        repo_full_name: str,
        max_evaluations_per_pr: int,
        approval_threshold: float,
        enable_cross_check: bool,
        pr_evaluation_enabled: bool,
        max_chunks_per_rule: int = 5,
        llm_model: Optional[str] = None,
        llm_primary_model: Optional[str] = None,
        llm_secondary_model: Optional[str] = None,
    ) -> Dict[str, Any]: ...
