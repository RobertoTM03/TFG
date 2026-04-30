import json
from contextlib import contextmanager
from typing import Any, Dict, Generator, List, Optional, Tuple

import psycopg2
import psycopg2.extras
import psycopg2.pool
from loguru import logger

# Whitelisted sort columns per entity
_TASK_SORT_COLUMNS = {"created_at", "status", "repository_full_name", "progress", "completed_at", "pr_number"}
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
                           (user_id, repository_full_name, rule_text, position, enabled)
                       VALUES (%s, %s, %s, %s, TRUE)
                       RETURNING *""",
                    (user_id, repo_full_name, rule_text, next_pos),
                )
                row = cur.fetchone()
            conn.commit()
            return dict(row)

    def update_rule(
        self,
        rule_id: str,
        user_id: str,
        rule_text: str = None,
        enabled: bool = None,
    ) -> dict | None:
        sets = []
        vals = []
        if rule_text is not None:
            sets.append("rule_text = %s")
            vals.append(rule_text)
        if enabled is not None:
            sets.append("enabled = %s")
            vals.append(enabled)
        if not sets:
            return None
        vals.extend([rule_id, user_id])
        with self._conn() as conn:
            with conn.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor,
            ) as cur:
                cur.execute(
                    f"""UPDATE rules SET {', '.join(sets)}
                        WHERE id = %s AND user_id = %s
                        RETURNING *""",
                    vals,
                )
                row = cur.fetchone()
            conn.commit()
            return dict(row) if row else None

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
        pr_head_ref: Optional[str] = None,
        pr_author: Optional[str] = None,
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
                            pr_number, pr_head_sha, pr_head_ref, pr_author,
                            github_installation_id)
                       VALUES (%s, %s, %s, %s, 'pending', %s, %s, %s, %s, %s, %s)
                       RETURNING *""",
                    (user_id, repository_url, repository_full_name,
                     json.dumps(rules), enable_cross_check,
                     pr_number, pr_head_sha, pr_head_ref, pr_author,
                     github_installation_id),
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
        self,
        user_id: str,
        repository_full_name: Optional[str] = None,
        pr_author: Optional[str] = None,
        status: Optional[str] = None,
    ) -> int:
        conditions = ["user_id = %s"]
        params: List[Any] = [user_id]
        if repository_full_name:
            conditions.append("repository_full_name = %s")
            params.append(repository_full_name)
        if pr_author:
            conditions.append("pr_author = %s")
            params.append(pr_author)
        if status:
            conditions.append("status = %s")
            params.append(status)
        where = " AND ".join(conditions)
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(f"SELECT COUNT(*) FROM tasks WHERE {where}", params)
                return cur.fetchone()[0]

    def get_user_tasks(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        repository_full_name: Optional[str] = None,
        pr_author: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        col = sort_by if sort_by in _TASK_SORT_COLUMNS else "created_at"
        order = "DESC" if sort_order.lower() == "desc" else "ASC"
        offset = (page - 1) * page_size
        conditions = ["user_id = %s"]
        params: List[Any] = [user_id]
        if repository_full_name:
            conditions.append("repository_full_name = %s")
            params.append(repository_full_name)
        if pr_author:
            conditions.append("pr_author = %s")
            params.append(pr_author)
        if status:
            conditions.append("status = %s")
            params.append(status)
        where = " AND ".join(conditions)
        params += [page_size, offset]
        with self._conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    f"""SELECT * FROM tasks
                        WHERE {where}
                        ORDER BY {col} {order}
                        LIMIT %s OFFSET %s""",
                    params,
                )
                return [dict(r) for r in cur.fetchall()]

    def claim_pending_task(self) -> Optional[Dict[str, Any]]:
        """Atomically claim the oldest pending task that is ready to run."""
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
                             AND (retry_after IS NULL OR retry_after <= NOW())
                           ORDER BY created_at ASC
                           LIMIT 1
                           FOR UPDATE SKIP LOCKED
                       )
                       RETURNING *"""
                )
                row = cur.fetchone()
            conn.commit()
            return dict(row) if row else None

    def requeue_task(self, task_id: str, delay_seconds: int) -> None:
        """Return a failed task to the pending queue to be retried after a delay."""
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE tasks
                       SET status = 'pending',
                           retry_count = retry_count + 1,
                           retry_after = NOW() + %s * INTERVAL '1 second',
                           started_at = NULL,
                           error = NULL,
                           progress_message = 'El servicio está experimentando problemas temporales. La evaluación se reanudará automáticamente.'
                       WHERE id = %s""",
                    (delay_seconds, task_id),
                )
            conn.commit()

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

    def save_task_partial_result(self, task_id: str, partial: list) -> None:
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE tasks SET partial_result = %s WHERE id = %s",
                    (json.dumps(partial), task_id),
                )
            conn.commit()

    def get_task_partial_result(self, task_id: str) -> list:
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT partial_result FROM tasks WHERE id = %s", (task_id,),
                )
                row = cur.fetchone()
            if row and row[0]:
                return row[0] if isinstance(row[0], list) else json.loads(row[0])
            return []

    def complete_task(self, task_id: str, result: dict) -> None:
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE tasks
                       SET status = 'completed',
                           progress = 100,
                           progress_message = 'Done',
                           result = %s,
                           partial_result = NULL,
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

    # Repositories (hub table for the indexing subsystem)

    def _get_or_create_repository(
        self,
        conn,
        url: str,
        full_name: Optional[str] = None,
    ) -> str:
        """Return repositories.id, creating the row if needed."""
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO repositories (url, full_name)
                   VALUES (%s, %s)
                   ON CONFLICT (url) DO UPDATE SET
                       full_name = COALESCE(EXCLUDED.full_name, repositories.full_name)
                   RETURNING id""",
                (url, full_name),
            )
            return str(cur.fetchone()[0])

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
                    """SELECT ir.* FROM indexed_repositories ir
                       JOIN repositories r ON ir.repository_id = r.id
                       WHERE r.url = %s
                         AND ir.embedding_model = %s
                         AND ir.chunking_strategy = %s""",
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
        repo_full_name: Optional[str] = None,
    ) -> str:
        """Upsert the indexed-repo record and return its id."""
        with self._conn() as conn:
            repo_id = self._get_or_create_repository(conn, repo_url, repo_full_name)
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO indexed_repositories
                           (repository_id, collection_name, num_chunks,
                            embedding_model, chunking_strategy)
                       VALUES (%s, %s, %s, %s, %s)
                       ON CONFLICT (repository_id, embedding_model, chunking_strategy)
                       DO UPDATE SET
                           collection_name = EXCLUDED.collection_name,
                           num_chunks      = EXCLUDED.num_chunks,
                           indexed_at      = NOW()
                       RETURNING id""",
                    (repo_id, collection_name, num_chunks,
                     embedding_model, chunking_strategy),
                )
                ir_id = str(cur.fetchone()[0])
            conn.commit()
        return ir_id

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
                    """SELECT fh.file_path, fh.content_hash
                       FROM file_hashes fh
                       JOIN indexed_repositories ir ON fh.indexed_repository_id = ir.id
                       JOIN repositories r ON ir.repository_id = r.id
                       WHERE r.url = %s
                         AND ir.embedding_model = %s
                         AND ir.chunking_strategy = %s""",
                    (repo_url, embedding_model, chunking_strategy),
                )
                return {row[0]: row[1] for row in cur.fetchall()}

    def save_file_hashes(
        self,
        indexed_repo_id: str,
        file_hashes: Dict[str, str],
    ) -> None:
        with self._conn() as conn:
            with conn.cursor() as cur:
                for file_path, content_hash in file_hashes.items():
                    cur.execute(
                        """INSERT INTO file_hashes
                               (indexed_repository_id, file_path, content_hash)
                           VALUES (%s, %s, %s)
                           ON CONFLICT (indexed_repository_id, file_path)
                           DO UPDATE SET
                               content_hash = EXCLUDED.content_hash,
                               updated_at   = NOW()""",
                        (indexed_repo_id, file_path, content_hash),
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
                       ORDER BY r.created_at ASC
                       LIMIT 1""",
                    (repo_full_name,),
                )
                row = cur.fetchone()
            return dict(row) if row else None

    # Repo configuration

    def get_repo_config(
        self, user_id: str, repo_full_name: str
    ) -> Optional[Dict[str, Any]]:
        """Return the config row for a repo, or None if not yet set."""
        with self._conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """SELECT * FROM repo_configs
                       WHERE user_id = %s AND repository_full_name = %s""",
                    (user_id, repo_full_name),
                )
                row = cur.fetchone()
            return dict(row) if row else None

    def upsert_repo_config(
        self,
        user_id: str,
        repo_full_name: str,
        max_evaluations_per_pr: int,
        approval_threshold: float,
        enable_cross_check: bool,
        pr_evaluation_enabled: bool,
        max_chunks_per_rule: int = 5,
    ) -> Dict[str, Any]:
        """Insert or update the config for a repo."""
        with self._conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """INSERT INTO repo_configs
                           (user_id, repository_full_name, max_evaluations_per_pr,
                            approval_threshold, enable_cross_check, pr_evaluation_enabled,
                            max_chunks_per_rule)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)
                       ON CONFLICT (user_id, repository_full_name) DO UPDATE SET
                           max_evaluations_per_pr = EXCLUDED.max_evaluations_per_pr,
                           approval_threshold      = EXCLUDED.approval_threshold,
                           enable_cross_check      = EXCLUDED.enable_cross_check,
                           pr_evaluation_enabled   = EXCLUDED.pr_evaluation_enabled,
                           max_chunks_per_rule     = EXCLUDED.max_chunks_per_rule,
                           updated_at              = NOW()
                       RETURNING *""",
                    (user_id, repo_full_name, max_evaluations_per_pr,
                     approval_threshold, enable_cross_check, pr_evaluation_enabled,
                     max_chunks_per_rule),
                )
                row = cur.fetchone()
            conn.commit()
            return dict(row)

    def count_pr_tasks(self, repo_full_name: str, pr_number: int) -> int:
        """Count how many tasks have already been created for a given PR."""
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT COUNT(*) FROM tasks
                       WHERE repository_full_name = %s AND pr_number = %s""",
                    (repo_full_name, pr_number),
                )
                return cur.fetchone()[0]

    # Contributors

    def get_repo_contributors(
        self, user_id: str, repo_full_name: str
    ) -> List[Dict[str, Any]]:
        """Return one row per contributor (pr_author) who has submitted to a repo,
        with submission count and latest task info."""
        with self._conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """WITH latest AS (
                           SELECT DISTINCT ON (pr_author)
                               pr_author,
                               id            AS last_task_id,
                               status        AS last_status,
                               created_at    AS last_submitted_at
                           FROM tasks
                           WHERE user_id = %s
                             AND repository_full_name = %s
                             AND pr_author IS NOT NULL
                           ORDER BY pr_author, created_at DESC
                       ),
                       counts AS (
                           SELECT pr_author, COUNT(*) AS submissions
                           FROM tasks
                           WHERE user_id = %s
                             AND repository_full_name = %s
                             AND pr_author IS NOT NULL
                           GROUP BY pr_author
                       )
                       SELECT l.pr_author,
                              l.last_task_id,
                              l.last_status,
                              l.last_submitted_at,
                              c.submissions
                       FROM latest l
                       JOIN counts c USING (pr_author)
                       ORDER BY l.last_submitted_at DESC""",
                    (user_id, repo_full_name, user_id, repo_full_name),
                )
                return [dict(r) for r in cur.fetchall()]

    def get_all_contributors(self, user_id: str) -> List[Dict[str, Any]]:
        """Return one row per contributor (pr_author) across all repositories
        owned by this user, with aggregated submission counts."""
        with self._conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """WITH task_agg AS (
                           SELECT
                               pr_author,
                               id,
                               status,
                               repository_full_name,
                               created_at
                           FROM tasks
                           WHERE user_id = %s
                             AND pr_author IS NOT NULL
                             AND pr_author <> ''
                       ),
                       latest AS (
                           SELECT DISTINCT ON (pr_author)
                               pr_author,
                               id            AS last_task_id,
                               status        AS last_status,
                               created_at    AS last_submitted_at
                           FROM task_agg
                           ORDER BY pr_author, created_at DESC
                       ),
                       agg AS (
                           SELECT
                               pr_author,
                               COUNT(*)                                          AS total_submissions,
                               COUNT(*) FILTER (WHERE status = 'completed')      AS completed_submissions,
                               COUNT(DISTINCT repository_full_name)              AS repo_count
                           FROM task_agg
                           GROUP BY pr_author
                       )
                       SELECT
                           a.pr_author,
                           a.total_submissions,
                           a.completed_submissions,
                           a.repo_count,
                           l.last_task_id,
                           l.last_status,
                           l.last_submitted_at
                       FROM agg a
                       JOIN latest l USING (pr_author)
                       ORDER BY l.last_submitted_at DESC""",
                    (user_id,),
                )
                return [dict(r) for r in cur.fetchall()]

    def get_contributor_repo_stats(
        self, user_id: str, github_login: str
    ) -> List[Dict[str, Any]]:
        """Return one row per repository the contributor has submitted to, with
        per-repo submission counts and the rule-verdict breakdown of their most
        recent completed task."""
        with self._conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """WITH contributor_tasks AS (
                           SELECT
                               id,
                               repository_full_name,
                               pr_number,
                               created_at,
                               status,
                               result
                           FROM tasks
                           WHERE user_id = %s
                             AND pr_author = %s
                             AND pr_author IS NOT NULL
                       ),
                       latest_completed_per_repo AS (
                           SELECT DISTINCT ON (repository_full_name)
                               repository_full_name,
                               id        AS best_task_id,
                               pr_number AS best_pr_number,
                               result    AS best_result
                           FROM contributor_tasks
                           WHERE status = 'completed' AND result IS NOT NULL
                           ORDER BY repository_full_name, created_at DESC
                       ),
                       repo_stats AS (
                           SELECT
                               repository_full_name,
                               COUNT(*)                                         AS total_submissions,
                               COUNT(*) FILTER (WHERE status = 'completed')     AS completed_submissions,
                               MAX(created_at)                                  AS last_submitted_at
                           FROM contributor_tasks
                           GROUP BY repository_full_name
                       )
                       SELECT
                           rs.repository_full_name,
                           rs.total_submissions,
                           rs.completed_submissions,
                           rs.last_submitted_at,
                           lc.best_task_id,
                           lc.best_pr_number,
                           lc.best_result
                       FROM repo_stats rs
                       LEFT JOIN latest_completed_per_repo lc USING (repository_full_name)
                       ORDER BY rs.last_submitted_at DESC""",
                    (user_id, github_login),
                )
                return [dict(r) for r in cur.fetchall()]

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
                    """DELETE FROM file_hashes fh
                       USING indexed_repositories ir, repositories r
                       WHERE fh.indexed_repository_id = ir.id
                         AND ir.repository_id = r.id
                         AND r.url = %s
                         AND ir.embedding_model = %s
                         AND ir.chunking_strategy = %s
                         AND fh.file_path = ANY(%s)""",
                    (repo_url, embedding_model, chunking_strategy, file_paths),
                )
            conn.commit()
