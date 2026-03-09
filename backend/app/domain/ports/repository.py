from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Tuple


class RepositoryPort(ABC):
    """Port for git repository operations."""

    @abstractmethod
    def clone(self, url: str) -> Path: ...

    @abstractmethod
    def load_files(self, repo_path: Path) -> List[Tuple[str, str]]: ...

    @abstractmethod
    def cleanup(self, repo_path: Path) -> None: ...
