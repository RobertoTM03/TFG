from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

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


class RulesListResponse(BaseModel):
    rules: List[RuleResponse]
    count: int


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
    secondary_verdict: str
    secondary_confidence: float
    secondary_model: str
    strategy_used: str  # "consensus" | "confidence" | "conservative"
    agreement: bool


class RuleValidationResponse(BaseModel):
    rule: str
    related_files: List[FileMatchResponse]
    match_count: int
    evaluation: Optional[RuleEvaluationResponse] = None
    cross_check: Optional[CrossCheckResponse] = None


class TaskResultResponse(BaseModel):
    repomap: str
    summary: str = ""
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


class HealthResponse(BaseModel):
    status: str
    components: Dict[str, bool]
    config: Dict[str, str]


