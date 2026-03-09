from abc import ABC, abstractmethod
from pathlib import Path


class RepomapPort(ABC):
    """Port for generating repository structure maps with code symbols."""

    @abstractmethod
    def generate(self, repo_path: Path) -> str: ...
