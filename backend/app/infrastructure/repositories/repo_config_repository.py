from typing import Any, Dict, Optional

import psycopg2.extras

from app.domain.ports.connection_provider import ConnectionProviderPort
from app.domain.ports.repo_config_repository import RepoConfigRepositoryPort


class RepoConfigRepository(RepoConfigRepositoryPort):
    def __init__(self, conn_provider: ConnectionProviderPort) -> None:
        self._conn = conn_provider.connection

    def get_repo_config(
        self, user_id: str, repo_full_name: str
    ) -> Optional[Dict[str, Any]]:
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
        llm_model: Optional[str] = None,
        llm_primary_model: Optional[str] = None,
        llm_secondary_model: Optional[str] = None,
    ) -> Dict[str, Any]:
        with self._conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """INSERT INTO repo_configs
                           (user_id, repository_full_name, max_evaluations_per_pr,
                            approval_threshold, enable_cross_check, pr_evaluation_enabled,
                            max_chunks_per_rule, llm_model, llm_primary_model, llm_secondary_model)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                       ON CONFLICT (user_id, repository_full_name) DO UPDATE SET
                           max_evaluations_per_pr = EXCLUDED.max_evaluations_per_pr,
                           approval_threshold      = EXCLUDED.approval_threshold,
                           enable_cross_check      = EXCLUDED.enable_cross_check,
                           pr_evaluation_enabled   = EXCLUDED.pr_evaluation_enabled,
                           max_chunks_per_rule     = EXCLUDED.max_chunks_per_rule,
                           llm_model               = EXCLUDED.llm_model,
                           llm_primary_model       = EXCLUDED.llm_primary_model,
                           llm_secondary_model     = EXCLUDED.llm_secondary_model,
                           updated_at              = NOW()
                       RETURNING *""",
                    (user_id, repo_full_name, max_evaluations_per_pr,
                     approval_threshold, enable_cross_check, pr_evaluation_enabled,
                     max_chunks_per_rule, llm_model, llm_primary_model, llm_secondary_model),
                )
                row = cur.fetchone()
            conn.commit()
            return dict(row)
