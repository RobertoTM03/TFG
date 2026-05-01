from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple


class RuleRepositoryPort(ABC):
    @abstractmethod
    def get_rules(
        self,
        user_id: str,
        repo_full_name: str,
        page: int = 1,
        page_size: int = 50,
        sort_by: str = "position",
        sort_order: str = "asc",
    ) -> Tuple[List[Dict[str, Any]], int]: ...

    @abstractmethod
    def count_rules(self, user_id: str, repo_full_name: str) -> int: ...

    @abstractmethod
    def create_rule(
        self, user_id: str, repo_full_name: str, rule_text: str,
    ) -> Dict[str, Any]: ...

    @abstractmethod
    def update_rule(
        self,
        rule_id: str,
        user_id: str,
        rule_text: Optional[str] = None,
        enabled: Optional[bool] = None,
    ) -> Optional[Dict[str, Any]]: ...

    @abstractmethod
    def delete_rule(self, rule_id: str, user_id: str) -> bool: ...
