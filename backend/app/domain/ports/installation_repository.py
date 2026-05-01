from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class InstallationRepositoryPort(ABC):
    @abstractmethod
    def upsert_installation(
        self, installation_id: int, user_id: str, account_login: str,
    ) -> None: ...

    @abstractmethod
    def delete_installation(self, installation_id: int) -> None: ...

    @abstractmethod
    def get_installation_by_id(
        self, installation_id: int,
    ) -> Optional[Dict[str, Any]]: ...

    @abstractmethod
    def get_installation_for_owner(
        self, user_id: str, account_login: str,
    ) -> Optional[Dict[str, Any]]: ...

    @abstractmethod
    def get_owner_for_repo(
        self, repo_full_name: str,
    ) -> Optional[Dict[str, Any]]: ...
