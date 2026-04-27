from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from app.domain.models.chunk import CodeChunk, SearchResult


class VectorStorePort(ABC):
    """Port for vector store operations (indexing and similarity search)."""

    @abstractmethod
    def index_documents(
        self,
        chunks: List[CodeChunk],
        collection_name: str,
        branch: str = '',
    ) -> int: ...

    @abstractmethod
    def similarity_search(
        self,
        query: str,
        collection_name: str,
        threshold: float = 0.3,
        max_results: int = 5,
        filter_metadata: Optional[Dict] = None,
        pr_branch: Optional[str] = None,
    ) -> List[SearchResult]: ...

    @abstractmethod
    def collection_exists(self, collection_name: str) -> bool: ...

    @abstractmethod
    def delete_collection(self, collection_name: str) -> None: ...

    @abstractmethod
    def delete_by_sources(
        self,
        collection_name: str,
        source_paths: List[str],
        branch: str = '',
    ) -> int: ...

    @abstractmethod
    def delete_branch(self, collection_name: str, branch: str) -> int: ...

    @abstractmethod
    def collection_count(self, collection_name: str) -> int: ...

    @abstractmethod
    def check_health(self) -> bool: ...
