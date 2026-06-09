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


class UpdateRuleRequest(BaseModel):
    """Body for PATCH /api/repos/{owner}/{repo}/rules/{rule_id}."""
    rule_text: Optional[str] = Field(None, min_length=1, max_length=500)
    enabled: Optional[bool] = None


class RuleResponse(BaseModel):
    id: str
    rule_text: str
    position: int
    enabled: bool = True


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
    explanation: str
    suggestions: List[str] = []
    llm_provider: str = ""
    tokens_used: int = 0


class CrossCheckResponse(BaseModel):
    """Audit log produced when a rule is evaluated by two models independently."""

    primary_verdict: str
    primary_model: str
    primary_explanation: str = ""
    secondary_verdict: str
    secondary_model: str
    secondary_explanation: str = ""
    agreement: bool
    discriminator_used: bool
    discriminator_model: Optional[str] = None
    discriminator_reasoning: Optional[str] = None


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
    processing_time_seconds: float = 0.0


class TaskSummaryResponse(BaseModel):
    """Lightweight task representation for listing."""
    id: str
    repository_full_name: str
    status: str
    progress: int
    progress_message: str
    created_at: str
    completed_at: Optional[str] = None
    pr_number: Optional[int] = None
    pr_author: Optional[str] = None


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
    pr_number: Optional[int] = None
    pr_head_ref: Optional[str] = None
    pr_head_sha: Optional[str] = None
    pr_author: Optional[str] = None
    enable_cross_check: bool = False
    retry_count: int = 0


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated list wrapper returned by list endpoints."""
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int


class RepoConfigResponse(BaseModel):
    """Per-repository configuration."""
    max_evaluations_per_pr: int
    approval_threshold: float
    enable_cross_check: bool
    pr_evaluation_enabled: bool
    max_chunks_per_rule: int
    llm_model: Optional[str] = None
    llm_primary_model: Optional[str] = None
    llm_secondary_model: Optional[str] = None


class RepoConfigRequest(BaseModel):
    """Body for PUT /api/repos/{owner}/{repo}/config."""
    max_evaluations_per_pr: int = Field(default=3, ge=1, le=20)
    approval_threshold: float = Field(default=0.8, ge=0.0, le=1.0)
    enable_cross_check: bool = True
    pr_evaluation_enabled: bool = True
    max_chunks_per_rule: int = Field(default=5, ge=1, le=20)
    llm_model: Optional[str] = None
    llm_primary_model: Optional[str] = None
    llm_secondary_model: Optional[str] = None


class ContributorSummaryResponse(BaseModel):
    """Aggregated view of a contributor's submissions for a single repository."""
    pr_author: str
    submissions: int
    last_status: Optional[str] = None
    last_submitted_at: Optional[str] = None
    last_task_id: Optional[str] = None


class ContributorOverviewResponse(BaseModel):
    """Aggregated view of a contributor across all repositories of the owner."""
    pr_author: str
    total_submissions: int
    completed_submissions: int
    repo_count: int
    last_status: Optional[str] = None
    last_submitted_at: Optional[str] = None
    last_task_id: Optional[str] = None


class ContributorRepoStatsResponse(BaseModel):
    """Per-repository breakdown for one contributor."""
    repository_full_name: str
    total_submissions: int
    completed_submissions: int
    best_task_id: Optional[str] = None
    best_pr_number: Optional[int] = None
    pass_count: int = 0
    partial_count: int = 0
    fail_count: int = 0
    last_submitted_at: Optional[str] = None


class ContributorDetailResponse(BaseModel):
    """Full summary for a single contributor: overall stats + per-repo breakdown."""
    pr_author: str
    total_submissions: int = 0
    completed_submissions: int = 0
    repos: List[ContributorRepoStatsResponse] = []


class HealthResponse(BaseModel):
    status: str
    components: Dict[str, bool]
    config: Dict[str, str]


