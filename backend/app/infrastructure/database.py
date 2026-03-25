import json
from contextlib import contextmanager
from typing import Any, Dict, Generator, List, Optional, Tuple

import psycopg2
import psycopg2.extras
import psycopg2.pool
from loguru import logger

# Whitelisted sort columns per entity
_TASK_SORT_COLUMNS = {"created_at", "status", "repository_full_name", "progress"}
_RULE_SORT_COLUMNS = {"position", "rule_text"}

_POOL_MIN = 2
_POOL_MAX = 10


class Database:
    """Single entry point for all SQL operations.

    Uses a ThreadedConnectionPool so connections are reused across requests
    instead of being created and destroyed on every operation.
    """

    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        dbname: str,
    ) -> None:
        self._pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=_POOL_MIN,
            maxconn=_POOL_MAX,
            host=host,
            port=port,
            user=user,
            password=password,
            dbname=dbname,
        )
        logger.info(
            f"Database connection pool created "
            f"(min={_POOL_MIN}, max={_POOL_MAX})"
        )

    def close(self) -> None:
        """Close all connections in the pool (call on application shutdown)."""
        self._pool.closeall()
        logger.info("Database connection pool closed")

    @contextmanager
    def _conn(self) -> Generator:
        """Yield a connection from the pool and return it when done."""
        conn = self._pool.getconn()
        try:
            yield conn
        finally:
            self._pool.putconn(conn)

    def check_health(self) -> bool:
        try:
            with self._conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
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
        with self._conn() as conn:
            with conn.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor,
            ) as cur:
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
            with conn.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor,
            ) as cur:
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

    def get_installation_for_owner(
        self, user_id: str, account_login: str
    ) -> Optional[Dict[str, Any]]:
        """Return the installation row for a given user + repo owner (account_login)."""
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

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        with self._conn() as conn:
            with conn.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor,
            ) as cur:
                cur.execute(
                    "SELECT * FROM users WHERE id = %s", (user_id,),
                )
                row = cur.fetchone()
            return dict(row) if row else None

    # Rules

    def get_rules(
        self,
        user_id: str,
        repo_full_name: str,
        page: int = 1,
        page_size: int = 50,
        sort_by: str = "position",
        sort_order: str = "asc",
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Returns (rows, total_count) to support pagination."""
        col = sort_by if sort_by in _RULE_SORT_COLUMNS else "position"
        order = "ASC" if sort_order.lower() == "asc" else "DESC"
        offset = (page - 1) * page_size
        with self._conn() as conn:
            with conn.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor,
            ) as cur:
                cur.execute(
                    """SELECT COUNT(*) FROM rules
                       WHERE user_id = %s AND repository_full_name = %s""",
                    (user_id, repo_full_name),
                )
                total = cur.fetchone()["count"]
                cur.execute(
                    f"""SELECT * FROM rules
                        WHERE user_id = %s AND repository_full_name = %s
                        ORDER BY {col} {order}
                        LIMIT %s OFFSET %s""",
                    (user_id, repo_full_name, page_size, offset),
                )
                rows = [dict(r) for r in cur.fetchall()]
            return rows, total

    def count_rules(self, user_id: str, repo_full_name: str) -> int:
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT COUNT(*) FROM rules
                       WHERE user_id = %s AND repository_full_name = %s""",
                    (user_id, repo_full_name),
                )
                return cur.fetchone()[0]

    def create_rule(
        self, user_id: str, repo_full_name: str, rule_text: str,
    ) -> Dict[str, Any]:
        with self._conn() as conn:
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

    def delete_rule(self, rule_id: str, user_id: str) -> bool:
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM rules WHERE id = %s AND user_id = %s",
                    (rule_id, user_id),
                )
                deleted = cur.rowcount > 0
            conn.commit()
            return deleted

    # Tasks

    def create_task(
        self,
        repository_url: str,
        repository_full_name: str,
        rules: List[str],
        user_id: Optional[str] = None,
        enable_cross_check: bool = False,
        pr_number: Optional[int] = None,
        pr_head_sha: Optional[str] = None,
        github_installation_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        with self._conn() as conn:
            with conn.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor,
            ) as cur:
                cur.execute(
                    """INSERT INTO tasks
                           (user_id, repository_url, repository_full_name,
                            rules, status, enable_cross_check,
                            pr_number, pr_head_sha, github_installation_id)
                       VALUES (%s, %s, %s, %s, 'pending', %s, %s, %s, %s)
                       RETURNING *""",
                    (user_id, repository_url, repository_full_name,
                     json.dumps(rules), enable_cross_check,
                     pr_number, pr_head_sha, github_installation_id),
                )
                row = cur.fetchone()
            conn.commit()
            return dict(row)

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        with self._conn() as conn:
            with conn.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor,
            ) as cur:
                cur.execute("SELECT * FROM tasks WHERE id = %s", (task_id,))
                row = cur.fetchone()
            return dict(row) if row else None

    def can_view_task(self, task_id: str, user_id: str) -> bool:
        """Return True if user_id is the owner or an authorized viewer."""
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT 1 FROM tasks
                       WHERE id = %s AND user_id = %s
                       UNION ALL
                       SELECT 1 FROM task_viewers
                       WHERE task_id = %s AND user_id = %s
                       LIMIT 1""",
                    (task_id, user_id, task_id, user_id),
                )
                return cur.fetchone() is not None

    def count_user_tasks(
        self, user_id: str, repository_full_name: Optional[str] = None,
    ) -> int:
        with self._conn() as conn:
            with conn.cursor() as cur:
                if repository_full_name:
                    cur.execute(
                        """SELECT COUNT(*) FROM tasks
                           WHERE user_id = %s AND repository_full_name = %s""",
                        (user_id, repository_full_name),
                    )
                else:
                    cur.execute(
                        "SELECT COUNT(*) FROM tasks WHERE user_id = %s",
                        (user_id,),
                    )
                return cur.fetchone()[0]

    def get_user_tasks(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        repository_full_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        col = sort_by if sort_by in _TASK_SORT_COLUMNS else "created_at"
        order = "DESC" if sort_order.lower() == "desc" else "ASC"
        offset = (page - 1) * page_size
        with self._conn() as conn:
            with conn.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor,
            ) as cur:
                if repository_full_name:
                    cur.execute(
                        f"""SELECT * FROM tasks
                            WHERE user_id = %s AND repository_full_name = %s
                            ORDER BY {col} {order}
                            LIMIT %s OFFSET %s""",
                        (user_id, repository_full_name, page_size, offset),
                    )
                else:
                    cur.execute(
                        f"""SELECT * FROM tasks
                            WHERE user_id = %s
                            ORDER BY {col} {order}
                            LIMIT %s OFFSET %s""",
                        (user_id, page_size, offset),
                    )
                return [dict(r) for r in cur.fetchall()]

    def claim_pending_task(self) -> Optional[Dict[str, Any]]:
        """Atomically claim the oldest pending task."""
        with self._conn() as conn:
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

    def update_task_progress(
        self, task_id: str, progress: int, message: str,
    ) -> None:
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE tasks
                       SET progress = %s, progress_message = %s
                       WHERE id = %s""",
                    (progress, message, task_id),
                )
            conn.commit()

    def complete_task(self, task_id: str, result: dict) -> None:
        with self._conn() as conn:
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

    def fail_task(self, task_id: str, error: str) -> None:
        with self._conn() as conn:
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

    # Indexed repositories

    def get_indexed_repo(
        self,
        repo_url: str,
        embedding_model: str,
        chunking_strategy: str,
    ) -> Optional[Dict[str, Any]]:
        with self._conn() as conn:
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

    def save_indexed_repo(
        self,
        repo_url: str,
        collection_name: str,
        num_chunks: int,
        embedding_model: str,
        chunking_strategy: str,
    ) -> None:
        with self._conn() as conn:
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

    # File hashes (incremental indexing)

    def get_file_hashes(
        self,
        repo_url: str,
        embedding_model: str,
        chunking_strategy: str,
    ) -> Dict[str, str]:
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT file_path, content_hash FROM file_hashes
                       WHERE repository_url = %s
                         AND embedding_model = %s
                         AND chunking_strategy = %s""",
                    (repo_url, embedding_model, chunking_strategy),
                )
                return {row[0]: row[1] for row in cur.fetchall()}

    def save_file_hashes(
        self,
        repo_url: str,
        embedding_model: str,
        chunking_strategy: str,
        file_hashes: Dict[str, str],
    ) -> None:
        with self._conn() as conn:
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

    # GitHub App installations

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

    def get_owner_for_repo(self, repo_full_name: str) -> Optional[Dict[str, Any]]:
        """Return the user who has rules for this repo (treat as owner)."""
        with self._conn() as conn:
            with conn.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor,
            ) as cur:
                cur.execute(
                    """SELECT u.* FROM users u
                       JOIN rules r ON r.user_id = u.id
                       WHERE r.repository_full_name = %s
                       LIMIT 1""",
                    (repo_full_name,),
                )
                row = cur.fetchone()
            return dict(row) if row else None

    def delete_file_hash_entries(
        self,
        repo_url: str,
        embedding_model: str,
        chunking_strategy: str,
        file_paths: List[str],
    ) -> None:
        if not file_paths:
            return
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """DELETE FROM file_hashes
                       WHERE repository_url = %s
                         AND embedding_model = %s
                         AND chunking_strategy = %s
                         AND file_path = ANY(%s)""",
                    (repo_url, embedding_model, chunking_strategy, file_paths),
                )
            conn.commit()
