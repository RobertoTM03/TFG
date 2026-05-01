from abc import ABC, abstractmethod
from typing import Any, Dict, List


class ContributorRepositoryPort(ABC):
    @abstractmethod
    def get_repo_contributors(
        self, user_id: str, repo_full_name: str,
    ) -> List[Dict[str, Any]]: ...

    @abstractmethod
    def get_all_contributors(self, user_id: str) -> List[Dict[str, Any]]: ...

    @abstractmethod
    def get_contributor_repo_stats(
        self, user_id: str, github_login: str,
    ) -> List[Dict[str, Any]]: ...
