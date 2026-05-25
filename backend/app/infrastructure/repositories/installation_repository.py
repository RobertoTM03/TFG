from typing import Any, Dict, Optional

import psycopg2.extras

from app.domain.ports.connection_provider import ConnectionProviderPort
from app.domain.ports.installation_repository import InstallationRepositoryPort


class InstallationRepository(InstallationRepositoryPort):
    def __init__(self, conn_provider: ConnectionProviderPort) -> None:
        self._conn = conn_provider.connection

    def upsert_installation(
        self,
        installation_id: int,
        user_id: str,
        account_login: str,
    ) -> None:
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO installations (installation_id, user_id, account_login)
                       VALUES (%s, %s, %s)
                       ON CONFLICT (installation_id) DO UPDATE SET
                           account_login = EXCLUDED.account_login""",
                    (installation_id, user_id, account_login),
                )
            conn.commit()

    def delete_installation(self, installation_id: int) -> None:
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM installations WHERE installation_id = %s",
                    (installation_id,),
                )
            conn.commit()

    def get_installation_by_id(self, installation_id: int) -> Optional[Dict[str, Any]]:
        with self._conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM installations WHERE installation_id = %s",
                    (installation_id,),
                )
                row = cur.fetchone()
            return dict(row) if row else None

    def get_installation_for_owner(
        self, user_id: str, account_login: str
    ) -> Optional[Dict[str, Any]]:
        with self._conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """SELECT * FROM installations
                       WHERE user_id = %s AND account_login = %s
                       LIMIT 1""",
                    (user_id, account_login),
                )
                row = cur.fetchone()
            return dict(row) if row else None

    def get_owner_for_repo(self, repo_full_name: str) -> Optional[Dict[str, Any]]:
        with self._conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """SELECT u.* FROM users u
                       JOIN rules r ON r.user_id = u.id
                       WHERE r.repository_full_name = %s
                       ORDER BY r.created_at ASC
                       LIMIT 1""",
                    (repo_full_name,),
                )
                row = cur.fetchone()
            return dict(row) if row else None
