from abc import ABC, abstractmethod
from typing import List, Tuple

from app.domain.models.chunk import CodeChunk


class ChunkingPort(ABC):
    """Port for code-chunking strategies."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def chunk_files(
        self, files: List[Tuple[str, str]],
    ) -> List[CodeChunk]: ...
