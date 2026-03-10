import hashlib
import re
import time
from typing import Dict, List, Optional

import chromadb
from loguru import logger

from app.domain.models.chunk import CodeChunk, SearchResult
from app.domain.ports import EmbeddingPort, VectorStorePort


class ChromaVectorStoreAdapter(VectorStorePort):
    """ChromaDB vector store adapter using HTTP client for server mode."""

    def __init__(
        self,
        host: str,
        port: int,
        embeddings: EmbeddingPort,
        batch_size: int = 5,
        delay_between_batches: float = 4.0,
    ) -> None:
        self._client = chromadb.HttpClient(host=host, port=port)
        self._embeddings = embeddings
        self._batch_size = batch_size
        self._delay = delay_between_batches

    # Indexing

    def index_documents(
        self,
        chunks: List[CodeChunk],
        collection_name: str,
    ) -> int:
        collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

        total = len(chunks)
        indexed = 0

        for i in range(0, total, self._batch_size):
            batch_chunks = chunks[i : i + self._batch_size]

            batch_texts = [chunk.content for chunk in batch_chunks]
            batch_ids = [
                self._generate_id(chunk.file_path, chunk.content)
                for chunk in batch_chunks
            ]
            
            # Serialize CodeChunk metadata to dict
            batch_meta = []
            for chunk in batch_chunks:
                meta = {
                    "source": chunk.file_path,
                    "start_line": chunk.start_line,
                    "end_line": chunk.end_line,
                }
                if chunk.language:
                    meta["language"] = chunk.language
                if chunk.repo_name:
                    meta["repo_name"] = chunk.repo_name
                if chunk.node_type:
                    meta["tree_sitter_type"] = chunk.node_type
                if chunk.node_name:
                    meta["node_name"] = chunk.node_name
                    
                batch_meta.append(self._sanitize_metadata(meta))

            tries = 0
            max_tries = 3
            while tries < max_tries:
                try:
                    batch_embeddings = self._embeddings.embed_documents(
                        batch_texts,
                    )
                    collection.upsert(
                        documents=batch_texts,
                        embeddings=batch_embeddings,
                        metadatas=batch_meta,
                        ids=batch_ids,
                    )
                    indexed += len(batch_texts)
                    batch_num = (i // self._batch_size) + 1
                    total_batches = (total - 1) // self._batch_size + 1
                    logger.info(
                        f"Batch {batch_num}/{total_batches} indexed "
                        f"({indexed}/{total} chunks)"
                    )
                    break
                except Exception as e:
                    tries += 1
                    retry_delay = 60.0
                    match = re.search(r"(\d+\.?\d*)\s?s", str(e))
                    if match:
                        retry_delay = float(match.group(1))
                    logger.warning(
                        f"Batch error (attempt {tries}/{max_tries}): "
                        f"{str(e)[:200]}"
                    )
                    if tries < max_tries:
                        wait = retry_delay + 5
                        logger.info(f"Waiting {wait:.1f}s before retry...")
                        time.sleep(wait)
                    else:
                        logger.error(
                            f"Failed batch after {max_tries} attempts. "
                            "Skipping."
                        )

            if i + self._batch_size < total:
                time.sleep(self._delay)

        return indexed

    # Search

    def similarity_search(
        self,
        query: str,
        collection_name: str,
        threshold: float = 0.3,
        max_results: int = 5,
        filter_metadata: Optional[Dict] = None,
    ) -> List[SearchResult]:
        collection = self._client.get_collection(name=collection_name)
        query_embedding = self._embeddings.embed_query(query)

        query_params: Dict = {
            "query_embeddings": [query_embedding],
            "n_results": max_results,
            "include": ["documents", "metadatas", "distances"],
        }
        if filter_metadata:
            query_params["where"] = filter_metadata

        results = collection.query(**query_params)

        filtered: List[SearchResult] = []
        if not results["distances"] or not results["distances"][0]:
            return filtered

        for i, distance in enumerate(results["distances"][0]):
            similarity = 1.0 - distance
            if similarity >= threshold:
                meta = (
                    results["metadatas"][0][i] if results["metadatas"] else {}
                )
                content = (
                    results["documents"][0][i]
                    if results["documents"]
                    else ""
                )
                chunk = CodeChunk(
                    content=content,
                    file_path=meta.get("source", ""),
                    start_line=int(meta.get("start_line", -1)),
                    end_line=int(meta.get("end_line", -1)),
                    language=meta.get("language"),
                    repo_name=meta.get("repo_name"),
                    node_type=meta.get("tree_sitter_type"),
                    node_name=meta.get("node_name"),
                )
                filtered.append(
                    SearchResult(chunk=chunk, relevance_score=similarity)
                )

        filtered.sort(key=lambda r: r.relevance_score, reverse=True)
        return filtered

    # Collection management

    def collection_exists(self, collection_name: str) -> bool:
        try:
            self._client.get_collection(name=collection_name)
            return True
        except Exception:
            return False

    def delete_collection(self, collection_name: str) -> None:
        try:
            self._client.delete_collection(name=collection_name)
        except Exception:
            pass

    def delete_by_sources(
        self, collection_name: str, source_paths: List[str],
    ) -> int:
        collection = self._client.get_collection(name=collection_name)
        total_deleted = 0
        for source in source_paths:
            try:
                results = collection.get(
                    where={"source": source}, include=[],
                )
                if results and results["ids"]:
                    collection.delete(ids=results["ids"])
                    total_deleted += len(results["ids"])
            except Exception as e:
                logger.warning(
                    f"Failed to delete chunks for {source}: {e}"
                )
        return total_deleted

    def collection_count(self, collection_name: str) -> int:
        try:
            collection = self._client.get_collection(name=collection_name)
            return collection.count()
        except Exception:
            return 0

    def check_health(self) -> bool:
        try:
            self._client.heartbeat()
            return True
        except Exception:
            return False

    # Helpers

    @staticmethod
    def _generate_id(source: str, content: str) -> str:
        raw = f"{source}|{content}"
        return hashlib.md5(raw.encode()).hexdigest()

    @staticmethod
    def _sanitize_metadata(meta: Dict) -> Dict:
        sanitized = {}
        for k, v in meta.items():
            if isinstance(v, (str, int, float, bool)):
                sanitized[k] = v
            elif v is None:
                sanitized[k] = ""
            else:
                sanitized[k] = str(v)
        return sanitized
