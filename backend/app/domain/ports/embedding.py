from abc import ABC, abstractmethod
from typing import List


class EmbeddingPort(ABC):
    """Port for embedding model providers."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def default_rpm(self) -> int: ...

    @abstractmethod
    def embed_documents(self, texts: List[str]) -> List[List[float]]: ...

    @abstractmethod
    def embed_query(self, text: str) -> List[float]: ...
