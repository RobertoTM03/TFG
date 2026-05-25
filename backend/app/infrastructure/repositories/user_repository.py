from typing import Any, Dict, Optional

import psycopg2.extras

from app.domain.ports.connection_provider import ConnectionProviderPort
from app.domain.ports.user_repository import UserRepositoryPort


class UserRepository(UserRepositoryPort):
    def __init__(self, conn_provider: ConnectionProviderPort) -> None:
        self._conn = conn_provider.connection

    def upsert_user(
        self,
        github_id: int,
        github_login: str,
        avatar_url: str,
        access_token: str,
    ) -> Dict[str, Any]:
        with self._conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """INSERT INTO users
                           (github_id, github_login, avatar_url, access_token)
                       VALUES (%s, %s, %s, %s)
                       ON CONFLICT (github_id) DO UPDATE SET
                           github_login  = EXCLUDED.github_login,
                           avatar_url    = EXCLUDED.avatar_url,
                           access_token  = EXCLUDED.access_token,
                           last_login_at = NOW()
                       RETURNING *""",
                    (github_id, github_login, avatar_url, access_token),
                )
                row = cur.fetchone()
            conn.commit()
            return dict(row)

    def get_user_by_token(self, token: str) -> Optional[Dict[str, Any]]:
        with self._conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM users WHERE access_token = %s", (token,),
                )
                row = cur.fetchone()
            return dict(row) if row else None

    def get_user_by_github_login(self, login: str) -> Optional[Dict[str, Any]]:
        with self._conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT * FROM users WHERE github_login = %s", (login,))
                row = cur.fetchone()
            return dict(row) if row else None

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        with self._conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
                row = cur.fetchone()
            return dict(row) if row else None
