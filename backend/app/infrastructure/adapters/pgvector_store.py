import hashlib
import re
import time
from contextlib import contextmanager
from typing import Dict, Generator, List, Optional

import psycopg2.extras
from loguru import logger
from pgvector.psycopg2 import register_vector

from app.domain.models.chunk import CodeChunk, SearchResult
from app.domain.ports import ConnectionProviderPort, EmbeddingPort, VectorStorePort

_COL_MAP = {"tree_sitter_type": "node_type"}
_FILTERABLE = frozenset({"source", "language", "repo_name", "node_type", "node_name"})


class PgVectorStoreAdapter(VectorStorePort):
    """PostgreSQL + pgvector/pgvectorscale vector store."""

    def __init__(
        self,
        database: ConnectionProviderPort,
        embeddings: EmbeddingPort,
        embedding_model_key: str,
        embedding_dimensions: int,
        batch_size: int = 5,
        delay_between_batches: float = 4.0,
    ) -> None:
        self._db = database
        self._embeddings = embeddings
        self._model_key = embedding_model_key
        self._dims = embedding_dimensions
        self._batch_size = batch_size
        self._delay = delay_between_batches
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        # Phase 1: load extensions using a plain connection (register_vector
        # requires the vector type to already exist, so it cannot be called yet).
        with self._db.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "CREATE EXTENSION IF NOT EXISTS vectorscale CASCADE"
                )
            conn.commit()

        # Phase 2: vector type now exists — register it, validate dims, create table.
        with self._vector_conn() as conn:
            with conn.cursor() as cur:
                # Check whether the table already exists.
                cur.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE  table_schema = 'public'
                        AND    table_name   = 'document_embeddings'
                    )
                """)
                table_exists: bool = cur.fetchone()[0]

                if table_exists:
                    # Read the stored model key from the table comment.
                    cur.execute("""
                        SELECT obj_description('document_embeddings'::regclass, 'pg_class')
                    """)
                    stored_model = cur.fetchone()[0]

                    if stored_model != self._model_key:
                        logger.warning(
                            f"document_embeddings was built with model '{stored_model}' but "
                            f"current model is '{self._model_key}'. "
                            "Dropping table and clearing index metadata — "
                            "repositories will need to be re-indexed."
                        )
                        cur.execute("DROP TABLE document_embeddings")
                        cur.execute("DELETE FROM indexed_repositories")
                        # file_hashes rows cascade-delete via indexed_repository_id FK
                        table_exists = False

                if not table_exists:
                    cur.execute(f"""
                        CREATE TABLE document_embeddings (
                            id              UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
                            collection_name TEXT        NOT NULL,
                            branch          TEXT        NOT NULL DEFAULT '',
                            source          TEXT        NOT NULL,
                            start_line      INTEGER,
                            end_line        INTEGER,
                            language        TEXT,
                            repo_name       TEXT,
                            node_type       TEXT,
                            node_name       TEXT,
                            content         TEXT        NOT NULL,
                            chunk_hash      TEXT        NOT NULL,
                            embedding       vector({self._dims}) NOT NULL,
                            created_at      TIMESTAMPTZ DEFAULT NOW(),
                            UNIQUE (collection_name, branch, chunk_hash)
                        )
                    """)
                    cur.execute("""
                        COMMENT ON TABLE document_embeddings IS %s
                    """, (self._model_key,))
                    cur.execute("""
                        CREATE INDEX idx_doc_emb_ns
                            ON document_embeddings (collection_name, branch)
                    """)
                    cur.execute("""
                        CREATE INDEX idx_doc_emb_source
                            ON document_embeddings (collection_name, branch, source)
                    """)
                    # StreamingDiskANN index via pgvectorscale for high-performance ANN
                    cur.execute("""
                        CREATE INDEX idx_doc_emb_diskann
                            ON document_embeddings USING diskann (embedding)
                    """)
            conn.commit()
        logger.info(f"document_embeddings schema ready (dims={self._dims})")

    @contextmanager
    def _vector_conn(self) -> Generator:
        """Yield a pool connection with the pgvector type registered."""
        with self._db.connection() as conn:
            register_vector(conn)
            yield conn

    @staticmethod
    def _chunk_hash(file_path: str, content: str) -> str:
        return hashlib.md5(f"{file_path}|{content}".encode()).hexdigest()

    def index_documents(
        self,
        chunks: List[CodeChunk],
        collection_name: str,
        branch: str = '',
    ) -> int:
        total = len(chunks)
        indexed = 0

        for i in range(0, total, self._batch_size):
            batch = chunks[i : i + self._batch_size]
            texts = [c.content for c in batch]
            hashes = [self._chunk_hash(c.file_path, c.content) for c in batch]

            tries = 0
            while tries < 3:
                try:
                    embeddings = self._embeddings.embed_documents(texts)
                    with self._vector_conn() as conn:
                        with conn.cursor() as cur:
                            for chunk, emb, h in zip(batch, embeddings, hashes):
                                cur.execute("""
                                    INSERT INTO document_embeddings
                                        (collection_name, branch, source,
                                         start_line, end_line, language,
                                         repo_name, node_type, node_name,
                                         content, chunk_hash, embedding)
                                    VALUES (%s, %s, %s, %s, %s, %s,
                                            %s, %s, %s, %s, %s, %s)
                                    ON CONFLICT (collection_name, branch, chunk_hash)
                                    DO UPDATE SET
                                        source     = EXCLUDED.source,
                                        start_line = EXCLUDED.start_line,
                                        end_line   = EXCLUDED.end_line,
                                        language   = EXCLUDED.language,
                                        repo_name  = EXCLUDED.repo_name,
                                        node_type  = EXCLUDED.node_type,
                                        node_name  = EXCLUDED.node_name,
                                        content    = EXCLUDED.content,
                                        embedding  = EXCLUDED.embedding,
                                        created_at = NOW()
                                """, (
                                    collection_name, branch,
                                    chunk.file_path,
                                    chunk.start_line, chunk.end_line,
                                    chunk.language, chunk.repo_name,
                                    chunk.node_type, chunk.node_name,
                                    chunk.content, h, emb,
                                ))
                        conn.commit()
                    indexed += len(batch)
                    batch_num = i // self._batch_size + 1
                    total_batches = (total - 1) // self._batch_size + 1
                    logger.info(
                        f"Batch {batch_num}/{total_batches} indexed "
                        f"({indexed}/{total} chunks)"
                    )
                    break
                except Exception as e:
                    tries += 1
                    retry_delay = 60.0
                    m = re.search(r"(\d+\.?\d*)\s?s", str(e))
                    if m:
                        retry_delay = float(m.group(1))
                    logger.warning(
                        f"Batch error (attempt {tries}/3): {str(e)[:200]}"
                    )
                    if tries < 3:
                        wait = retry_delay + 5
                        logger.info(f"Waiting {wait:.1f}s before retry...")
                        time.sleep(wait)
                    else:
                        logger.error("Failed batch after 3 attempts. Skipping.")

            if i + self._batch_size < total:
                time.sleep(self._delay)

        return indexed

    def delete_by_sources(
        self,
        collection_name: str,
        source_paths: List[str],
        branch: str = '',
    ) -> int:
        if not source_paths:
            return 0
        with self._vector_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM document_embeddings
                    WHERE  collection_name = %s
                      AND  branch          = %s
                      AND  source          = ANY(%s)
                """, (collection_name, branch, source_paths))
                deleted = cur.rowcount
            conn.commit()
        return deleted

    def delete_collection(self, collection_name: str) -> None:
        with self._vector_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM document_embeddings
                    WHERE  collection_name = %s
                """, (collection_name,))
            conn.commit()

    def delete_branch(self, collection_name: str, branch: str) -> int:
        with self._vector_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM document_embeddings
                    WHERE  collection_name = %s
                      AND  branch          = %s
                """, (collection_name, branch))
                deleted = cur.rowcount
            conn.commit()
        return deleted

    def similarity_search(
        self,
        query: str,
        collection_name: str,
        threshold: float = 0.3,
        max_results: int = 5,
        filter_metadata: Optional[Dict] = None,
        pr_branch: Optional[str] = None,
    ) -> List[SearchResult]:
        query_emb = self._embeddings.embed_query(query)

        extra_clauses: list = []
        extra_params: list = []
        if filter_metadata:
            for key, val in filter_metadata.items():
                col = _COL_MAP.get(key, key)
                if col in _FILTERABLE:
                    extra_clauses.append(f"{col} = %s")
                    extra_params.append(val)

        if pr_branch is not None:
            rows = self._union_search(
                query_emb, collection_name, pr_branch,
                extra_clauses, extra_params, max_results,
            )
        else:
            rows = self._branch_search(
                query_emb, collection_name, '',
                extra_clauses, extra_params, max_results,
            )

        out: List[SearchResult] = []
        for row in rows:
            sim = float(row["similarity"])
            if sim >= threshold:
                chunk = CodeChunk(
                    content=row["content"],
                    file_path=row["source"],
                    start_line=int(row["start_line"] or -1),
                    end_line=int(row["end_line"] or -1),
                    language=row["language"],
                    repo_name=row["repo_name"],
                    node_type=row["node_type"],
                    node_name=row["node_name"],
                )
                out.append(SearchResult(chunk=chunk, relevance_score=sim))

        out.sort(key=lambda r: r.relevance_score, reverse=True)
        return out[:max_results]

    def _branch_search(
        self,
        query_emb,
        collection_name: str,
        branch: str,
        extra_clauses: list,
        extra_params: list,
        max_results: int,
    ) -> list:
        where = "collection_name = %s AND branch = %s"
        if extra_clauses:
            where += " AND " + " AND ".join(extra_clauses)

        sql = f"""
            SELECT source, start_line, end_line, language,
                   repo_name, node_type, node_name, content,
                   1.0 - (embedding <=> %s::vector) AS similarity
            FROM   document_embeddings
            WHERE  {where}
            ORDER  BY embedding <=> %s::vector
            LIMIT  %s
        """
        params = (
            [query_emb, collection_name, branch]
            + extra_params
            + [query_emb, max_results]
        )
        with self._vector_conn() as conn:
            with conn.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor,
            ) as cur:
                cur.execute(sql, params)
                return cur.fetchall()

    def _union_search(
        self,
        query_emb,
        collection_name: str,
        pr_branch: str,
        extra_clauses: list,
        extra_params: list,
        max_results: int,
    ) -> list:
        """Search main (branch='') and PR delta, deduplicate by file (PR wins)."""
        main_rows = self._branch_search(
            query_emb, collection_name, '',
            extra_clauses, extra_params, max_results,
        )
        pr_rows = self._branch_search(
            query_emb, collection_name, pr_branch,
            extra_clauses, extra_params, max_results,
        )

        # Merge: PR version overwrites main for the same source file
        merged: Dict[str, dict] = {row["source"]: row for row in main_rows}
        for row in pr_rows:
            merged[row["source"]] = row

        return sorted(merged.values(), key=lambda r: r["similarity"], reverse=True)

    def collection_exists(self, collection_name: str) -> bool:
        """Returns True only if the main branch (branch='') has been indexed."""
        with self._vector_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 1 FROM document_embeddings
                    WHERE  collection_name = %s
                      AND  branch          = ''
                    LIMIT  1
                """, (collection_name,))
                return cur.fetchone() is not None

    def collection_count(self, collection_name: str) -> int:
        with self._vector_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*) FROM document_embeddings
                    WHERE  collection_name = %s
                """, (collection_name,))
                row = cur.fetchone()
        return int(row[0]) if row else 0

    def check_health(self) -> bool:
        try:
            with self._vector_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
            return True
        except Exception:
            return False
