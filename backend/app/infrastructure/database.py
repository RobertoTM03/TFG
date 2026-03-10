import json
from typing import Any, Dict, List, Optional

import psycopg2
import psycopg2.extras
from loguru import logger


class Database:
    """Single entry point for all SQL operations."""

    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        dbname: str,
    ) -> None:
        self._conn_params = {
            "host": host,
            "port": port,
            "user": user,
            "password": password,
            "dbname": dbname,
        }

    def _conn(self):
        return psycopg2.connect(**self._conn_params)

    def check_health(self) -> bool:
        try:
            conn = self._conn()
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
            conn.close()
            return True
        except Exception:
            return False

    # Users

    def upsert_user(
        self,
        github_id: int,
        github_login: str,
        avatar_url: str,
        access_token: str,
    ) -> Dict[str, Any]:
        conn = self._conn()
        try:
            with conn.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor,
            ) as cur:
                cur.execute(
                    """INSERT INTO users
                           (github_id, github_login, avatar_url, access_token)
                       VALUES (%s, %s, %s, %s)
                       ON CONFLICT (github_id) DO UPDATE SET
                           github_login = EXCLUDED.github_login,
                           avatar_url   = EXCLUDED.avatar_url,
                           access_token = EXCLUDED.access_token,
                           last_login_at = NOW()
                       RETURNING *""",
                    (github_id, github_login, avatar_url, access_token),
                )
                row = cur.fetchone()
            conn.commit()
            return dict(row)
        finally:
            conn.close()

    def get_user_by_token(self, token: str) -> Optional[Dict[str, Any]]:
        conn = self._conn()
        try:
            with conn.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor,
            ) as cur:
                cur.execute(
                    "SELECT * FROM users WHERE access_token = %s", (token,),
                )
                row = cur.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    # Rules

    def get_rules(
        self, user_id: str, repo_full_name: str,
    ) -> List[Dict[str, Any]]:
        conn = self._conn()
        try:
            with conn.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor,
            ) as cur:
                cur.execute(
                    """SELECT * FROM rules
                       WHERE user_id = %s AND repository_full_name = %s
                       ORDER BY position""",
                    (user_id, repo_full_name),
                )
                return [dict(r) for r in cur.fetchall()]
        finally:
            conn.close()

    def count_rules(self, user_id: str, repo_full_name: str) -> int:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT COUNT(*) FROM rules
                       WHERE user_id = %s AND repository_full_name = %s""",
                    (user_id, repo_full_name),
                )
                return cur.fetchone()[0]
        finally:
            conn.close()

    def create_rule(
        self, user_id: str, repo_full_name: str, rule_text: str,
    ) -> Dict[str, Any]:
        conn = self._conn()
        try:
            with conn.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor,
            ) as cur:
                cur.execute(
                    """SELECT COALESCE(MAX(position), -1) + 1 AS next_pos
                       FROM rules
                       WHERE user_id = %s AND repository_full_name = %s""",
                    (user_id, repo_full_name),
                )
                next_pos = cur.fetchone()["next_pos"]

                cur.execute(
                    """INSERT INTO rules
                           (user_id, repository_full_name, rule_text, position)
                       VALUES (%s, %s, %s, %s)
                       RETURNING *""",
                    (user_id, repo_full_name, rule_text, next_pos),
                )
                row = cur.fetchone()
            conn.commit()
            return dict(row)
        finally:
            conn.close()

    def delete_rule(self, rule_id: str, user_id: str) -> bool:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM rules WHERE id = %s AND user_id = %s",
                    (rule_id, user_id),
                )
                deleted = cur.rowcount > 0
            conn.commit()
            return deleted
        finally:
            conn.close()

    # Tasks

    def create_task(
        self,
        repository_url: str,
        repository_full_name: str,
        rules: List[str],
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        conn = self._conn()
        try:
            with conn.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor,
            ) as cur:
                cur.execute(
                    """INSERT INTO tasks
                           (user_id, repository_url, repository_full_name,
                            rules, status)
                       VALUES (%s, %s, %s, %s, 'pending')
                       RETURNING *""",
                    (user_id, repository_url, repository_full_name,
                     json.dumps(rules)),
                )
                row = cur.fetchone()
            conn.commit()
            return dict(row)
        finally:
            conn.close()

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        conn = self._conn()
        try:
            with conn.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor,
            ) as cur:
                cur.execute("SELECT * FROM tasks WHERE id = %s", (task_id,))
                row = cur.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_user_tasks(
        self, user_id: str, limit: int = 50,
    ) -> List[Dict[str, Any]]:
        conn = self._conn()
        try:
            with conn.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor,
            ) as cur:
                cur.execute(
                    """SELECT * FROM tasks
                       WHERE user_id = %s
                       ORDER BY created_at DESC
                       LIMIT %s""",
                    (user_id, limit),
                )
                return [dict(r) for r in cur.fetchall()]
        finally:
            conn.close()

    def claim_pending_task(self) -> Optional[Dict[str, Any]]:
        """Atomically claim the oldest pending task."""
        conn = self._conn()
        try:
            with conn.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor,
            ) as cur:
                cur.execute(
                    """UPDATE tasks
                       SET status = 'running', started_at = NOW()
                       WHERE id = (
                           SELECT id FROM tasks
                           WHERE status = 'pending'
                           ORDER BY created_at ASC
                           LIMIT 1
                           FOR UPDATE SKIP LOCKED
                       )
                       RETURNING *"""
                )
                row = cur.fetchone()
            conn.commit()
            return dict(row) if row else None
        finally:
            conn.close()

    def update_task_progress(
        self, task_id: str, progress: int, message: str,
    ) -> None:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE tasks
                       SET progress = %s, progress_message = %s
                       WHERE id = %s""",
                    (progress, message, task_id),
                )
            conn.commit()
        finally:
            conn.close()

    def complete_task(self, task_id: str, result: dict) -> None:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE tasks
                       SET status = 'completed',
                           progress = 100,
                           progress_message = 'Done',
                           result = %s,
                           completed_at = NOW()
                       WHERE id = %s""",
                    (json.dumps(result), task_id),
                )
            conn.commit()
        finally:
            conn.close()

    def fail_task(self, task_id: str, error: str) -> None:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE tasks
                       SET status = 'failed',
                           error = %s,
                           completed_at = NOW()
                       WHERE id = %s""",
                    (error, task_id),
                )
            conn.commit()
        finally:
            conn.close()

    # Indexed repositories

    def get_indexed_repo(
        self,
        repo_url: str,
        embedding_model: str,
        chunking_strategy: str,
    ) -> Optional[Dict[str, Any]]:
        conn = self._conn()
        try:
            with conn.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor,
            ) as cur:
                cur.execute(
                    """SELECT * FROM indexed_repositories
                       WHERE repository_url = %s
                         AND embedding_model = %s
                         AND chunking_strategy = %s""",
                    (repo_url, embedding_model, chunking_strategy),
                )
                row = cur.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def save_indexed_repo(
        self,
        repo_url: str,
        collection_name: str,
        num_chunks: int,
        embedding_model: str,
        chunking_strategy: str,
    ) -> None:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO indexed_repositories
                           (repository_url, collection_name, num_chunks,
                            embedding_model, chunking_strategy)
                       VALUES (%s, %s, %s, %s, %s)
                       ON CONFLICT (repository_url, embedding_model,
                                    chunking_strategy)
                       DO UPDATE SET
                           collection_name = EXCLUDED.collection_name,
                           num_chunks = EXCLUDED.num_chunks,
                           indexed_at = NOW()""",
                    (repo_url, collection_name, num_chunks,
                     embedding_model, chunking_strategy),
                )
            conn.commit()
        finally:
            conn.close()

    # File hashes (incremental indexing)

    def get_file_hashes(
        self,
        repo_url: str,
        embedding_model: str,
        chunking_strategy: str,
    ) -> Dict[str, str]:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT file_path, content_hash FROM file_hashes
                       WHERE repository_url = %s
                         AND embedding_model = %s
                         AND chunking_strategy = %s""",
                    (repo_url, embedding_model, chunking_strategy),
                )
                return {row[0]: row[1] for row in cur.fetchall()}
        finally:
            conn.close()

    def save_file_hashes(
        self,
        repo_url: str,
        embedding_model: str,
        chunking_strategy: str,
        file_hashes: Dict[str, str],
    ) -> None:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                for file_path, content_hash in file_hashes.items():
                    cur.execute(
                        """INSERT INTO file_hashes
                               (repository_url, embedding_model,
                                chunking_strategy, file_path, content_hash)
                           VALUES (%s, %s, %s, %s, %s)
                           ON CONFLICT (repository_url, embedding_model,
                                        chunking_strategy, file_path)
                           DO UPDATE SET
                               content_hash = EXCLUDED.content_hash,
                               updated_at = NOW()""",
                        (repo_url, embedding_model, chunking_strategy,
                         file_path, content_hash),
                    )
            conn.commit()
        finally:
            conn.close()

    def delete_file_hash_entries(
        self,
        repo_url: str,
        embedding_model: str,
        chunking_strategy: str,
        file_paths: List[str],
    ) -> None:
        if not file_paths:
            return
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """DELETE FROM file_hashes
                       WHERE repository_url = %s
                         AND embedding_model = %s
                         AND chunking_strategy = %s
                         AND file_path = ANY(%s)""",
                    (repo_url, embedding_model, chunking_strategy,
                     file_paths),
                )
            conn.commit()
        finally:
            conn.close()
