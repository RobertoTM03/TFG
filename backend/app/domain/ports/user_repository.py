from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class UserRepositoryPort(ABC):
    @abstractmethod
    def upsert_user(
        self,
        github_id: int,
        github_login: str,
        avatar_url: str,
        access_token: str,
    ) -> Dict[str, Any]: ...

    @abstractmethod
    def get_user_by_token(self, token: str) -> Optional[Dict[str, Any]]: ...

    @abstractmethod
    def get_user_by_github_login(self, login: str) -> Optional[Dict[str, Any]]: ...

    @abstractmethod
    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]: ...
