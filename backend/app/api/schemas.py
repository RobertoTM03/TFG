from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")

# Requests

class CreateRuleRequest(BaseModel):
    """Body for POST /api/repos/{owner}/{repo}/rules."""
    rule_text: str = Field(
        ..., min_length=1, max_length=500,
        description="Rule text to evaluate against the repository",
    )

# Responses

class UserResponse(BaseModel):
    """Authenticated user info."""
    id: str
    github_id: int
    github_login: str
    avatar_url: str


class RuleResponse(BaseModel):
    id: str
    rule_text: str
    position: int


class TaskCreatedResponse(BaseModel):
    """Returned when a validation task is created (HTTP 202)."""
    task_id: str
    status: str = "pending"


class FileMatchResponse(BaseModel):
    file_path: str
    relevance_score: float
    file_content: str
    language: Optional[str] = None
    matched_symbols: List[str] = []
    truncated: bool = False


class RuleEvaluationResponse(BaseModel):
    """LLM evaluation of a single rule."""
    verdict: str  # "pass" | "fail" | "partial"
    confidence: float
    explanation: str
    suggestions: List[str] = []
    llm_provider: str = ""
    tokens_used: int = 0


class CrossCheckResponse(BaseModel):
    """Metadata produced when a rule is evaluated by two models independently."""

    primary_verdict: str
    primary_confidence: float
    primary_model: str
    primary_explanation: str = ""
    secondary_verdict: str
    secondary_confidence: float
    secondary_model: str
    secondary_explanation: str = ""
    strategy_used: str  # "consensus" | "confidence" | "conservative"
    agreement: bool


class RuleValidationResponse(BaseModel):
    rule: str
    related_files: List[FileMatchResponse]
    evaluation: Optional[RuleEvaluationResponse] = None
    cross_check: Optional[CrossCheckResponse] = None


class TaskResultResponse(BaseModel):
    validations: List[RuleValidationResponse]
    embedding_model: str
    chunking_strategy: str
    llm_model: str = ""


class TaskSummaryResponse(BaseModel):
    """Lightweight task representation for listing."""
    id: str
    repository_full_name: str
    status: str
    progress: int
    progress_message: str
    created_at: str


class TaskDetailResponse(BaseModel):
    """Full task detail including result when completed."""
    id: str
    repository_url: str
    repository_full_name: str
    rules: List[str]
    status: str
    progress: int
    progress_message: str
    result: Optional[TaskResultResponse] = None
    error: Optional[str] = None
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated list wrapper returned by list endpoints."""
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int


class RepoConfigResponse(BaseModel):
    """Per-repository configuration managed by the teacher."""
    max_evaluations_per_pr: int
    approval_threshold: float
    enable_cross_check: bool
    pr_evaluation_enabled: bool


class RepoConfigRequest(BaseModel):
    """Body for PUT /api/repos/{owner}/{repo}/config."""
    max_evaluations_per_pr: int = Field(default=3, ge=1, le=20)
    approval_threshold: float = Field(default=0.8, ge=0.0, le=1.0)
    enable_cross_check: bool = True
    pr_evaluation_enabled: bool = True


class HealthResponse(BaseModel):
    status: str
    components: Dict[str, bool]
    config: Dict[str, str]


