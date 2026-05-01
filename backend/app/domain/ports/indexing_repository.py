from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class IndexingRepositoryPort(ABC):
    @abstractmethod
    def get_file_hashes(
        self,
        repo_url: str,
        embedding_model: str,
        chunking_strategy: str,
    ) -> Dict[str, str]: ...

    @abstractmethod
    def delete_file_hash_entries(
        self,
        repo_url: str,
        embedding_model: str,
        chunking_strategy: str,
        file_paths: List[str],
    ) -> None: ...

    @abstractmethod
    def save_indexed_repo(
        self,
        repo_url: str,
        collection_name: str,
        num_chunks: int,
        embedding_model: str,
        chunking_strategy: str,
        repo_full_name: Optional[str] = None,
    ) -> str: ...

    @abstractmethod
    def save_file_hashes(
        self,
        indexed_repo_id: str,
        file_hashes: Dict[str, str],
    ) -> None: ...
