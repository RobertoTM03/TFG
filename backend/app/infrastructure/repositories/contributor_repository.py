from typing import Any, Dict, List

import psycopg2.extras

from app.domain.ports.connection_provider import ConnectionProviderPort
from app.domain.ports.contributor_repository import ContributorRepositoryPort


class ContributorRepository(ContributorRepositoryPort):
    def __init__(self, conn_provider: ConnectionProviderPort) -> None:
        self._conn = conn_provider.connection

    def get_repo_contributors(
        self, user_id: str, repo_full_name: str
    ) -> List[Dict[str, Any]]:
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
        with self._conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """WITH task_agg AS (
                           SELECT
                               id,
                               pr_author,
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
