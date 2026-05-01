from typing import Any, Dict

from app.domain.ports.user_repository import UserRepositoryPort


class AuthService:
    def __init__(self, user_repo: UserRepositoryPort) -> None:
        self._user_repo = user_repo

    def upsert_user(
        self,
        github_id: int,
        github_login: str,
        avatar_url: str,
        access_token: str,
    ) -> Dict[str, Any]:
        return self._user_repo.upsert_user(
            github_id=github_id,
            github_login=github_login,
            avatar_url=avatar_url,
            access_token=access_token,
        )
