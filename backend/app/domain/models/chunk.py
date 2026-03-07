from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class CodeChunk:
    """Represents a chunk of source code with metadata."""

    content: str
    file_path: str
    start_line: int = -1
    end_line: int = -1
    language: Optional[str] = None
    repo_name: Optional[str] = None
    node_type: Optional[str] = None
    node_name: Optional[str] = None
    extra_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchResult:
    """A chunk retrieved from similarity search with its relevance score."""

    chunk: CodeChunk
    relevance_score: float
