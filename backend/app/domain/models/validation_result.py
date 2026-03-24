from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from app.domain.models.cross_check import CrossCheckedEvaluation
from app.domain.models.evaluation import RuleEvaluation


@dataclass
class FileMatch:
    """A file matched by a rule, with full content (possibly truncated)."""

    file_path: str
    relevance_score: float
    file_content: str
    language: Optional[str] = None
    matched_symbols: List[str] = field(default_factory=list)
    truncated: bool = False


@dataclass
class RuleValidation:
    """Result of validating a single rule against a repository."""

    rule: str
    related_files: List[FileMatch] = field(default_factory=list)
    evaluation: Optional[RuleEvaluation] = None
    cross_check: Optional[CrossCheckedEvaluation] = None


@dataclass
class ValidationResult:
    """Complete result of validating rules against a repository."""

    id: Optional[str] = None
    repository_url: str = ""
    repomap: str = ""
    validations: List[RuleValidation] = field(default_factory=list)
    embedding_model: str = ""
    chunking_strategy: str = ""
    llm_model: str = ""
    similarity_threshold: float = 0.0
    total_chunks_indexed: int = 0
    processing_time_seconds: float = 0.0
    created_at: Optional[datetime] = None
