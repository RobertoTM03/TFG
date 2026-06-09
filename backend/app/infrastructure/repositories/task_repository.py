import json
from typing import Any, Dict, List, Optional

import psycopg2.extras

from app.domain.ports.connection_provider import ConnectionProviderPort
from app.domain.ports.task_repository import TaskRepositoryPort

_TASK_SORT_COLUMNS: Dict[str, str] = {
    "created_at": "created_at",
    "status": "status",
    "repository_full_name": "repository_full_name",
    "progress": "progress",
    "completed_at": "completed_at",
    "pr_number": "pr_number",
}
_TASK_SORT_DEFAULT = "created_at"


class TaskRepository(TaskRepositoryPort):
    def __init__(self, conn_provider: ConnectionProviderPort) -> None:
        self._conn = conn_provider.connection

    def create_task(
        self,
        repository_url: str,
        repository_full_name: str,
        rules: List[str],
        user_id: Optional[str] = None,
        enable_cross_check: bool = True,
        pr_number: Optional[int] = None,
        pr_head_sha: Optional[str] = None,
        pr_head_ref: Optional[str] = None,
        pr_author: Optional[str] = None,
        github_installation_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        with self._conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
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
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT * FROM tasks WHERE id = %s", (task_id,))
                row = cur.fetchone()
            return dict(row) if row else None

    def can_view_task(self, task_id: str, user_id: str) -> bool:
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

    def _build_task_filter(
        self,
        user_id: str,
        repository_full_name: Optional[str],
        pr_author: Optional[str],
        status: Optional[str],
    ):
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
        return " AND ".join(conditions), params

    def count_user_tasks(
        self,
        user_id: str,
        repository_full_name: Optional[str] = None,
        pr_author: Optional[str] = None,
        status: Optional[str] = None,
    ) -> int:
        where, params = self._build_task_filter(user_id, repository_full_name, pr_author, status)
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
        col = _TASK_SORT_COLUMNS.get(sort_by, _TASK_SORT_DEFAULT)
        order = "DESC" if sort_order.lower() == "desc" else "ASC"
        order_clause = f"{col} {order}"
        offset = (page - 1) * page_size
        where, params = self._build_task_filter(user_id, repository_full_name, pr_author, status)
        params += [page_size, offset]
        with self._conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    f"""SELECT * FROM tasks
                        WHERE {where}
                        ORDER BY {order_clause}
                        LIMIT %s OFFSET %s""",
                    params,
                )
                return [dict(r) for r in cur.fetchall()]

    def claim_pending_task(self) -> Optional[Dict[str, Any]]:
        with self._conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
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
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE tasks
                       SET status = 'pending',
                           retry_count = retry_count + 1,
                           retry_after = NOW() + %s * INTERVAL '1 second',
                           started_at = NULL,
                           error = NULL,
                           progress_message = 'Service temporarily unavailable. Evaluation will resume automatically.'
                       WHERE id = %s""",
                    (delay_seconds, task_id),
                )
            conn.commit()

    def update_task_progress(self, task_id: str, progress: int, message: str) -> None:
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

    def count_pr_tasks(self, repo_full_name: str, pr_number: int) -> int:
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT COUNT(*) FROM tasks
                       WHERE repository_full_name = %s AND pr_number = %s""",
                    (repo_full_name, pr_number),
                )
                return cur.fetchone()[0]
