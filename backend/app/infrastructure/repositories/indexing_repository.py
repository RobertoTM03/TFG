from typing import Any, Dict, List, Optional

import psycopg2.extras

from app.domain.ports.connection_provider import ConnectionProviderPort
from app.domain.ports.indexing_repository import IndexingRepositoryPort


class IndexingRepository(IndexingRepositoryPort):
    def __init__(self, conn_provider: ConnectionProviderPort) -> None:
        self._conn = conn_provider.connection

    def _get_or_create_repository(self, conn, url: str, full_name: Optional[str] = None) -> str:
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

    def get_indexed_repo(
        self,
        repo_url: str,
        embedding_model: str,
        chunking_strategy: str,
    ) -> Optional[Dict[str, Any]]:
        with self._conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
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
                    (repo_id, collection_name, num_chunks, embedding_model, chunking_strategy),
                )
                ir_id = str(cur.fetchone()[0])
            conn.commit()
        return ir_id

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

    def save_file_hashes(self, indexed_repo_id: str, file_hashes: Dict[str, str]) -> None:
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
