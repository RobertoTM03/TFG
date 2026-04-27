from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings

from app.domain.models.embedding_model import SUPPORTED_EMBEDDING_MODELS

_VALID_CHUNKING_STRATEGIES = {"tree-sitter", "tree-sitter-limited"}
_VALID_LLM_MODELS = {"gemini-2.5-flash","gemini-3.1-flash-lite-preview"}

class Settings(BaseSettings):
    """All configurable values for the application."""

    #  GitHub OAuth
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""
    GITHUB_CALLBACK_URL: str = "http://localhost:8080/auth/callback"
    FRONTEND_URL: str = "http://localhost:3000"

    # Embedding & Chunking
    EMBEDDING_MODEL: str = "gemini"
    CHUNKING_STRATEGY: str = "tree-sitter-limited"

    # API Keys
    GOOGLE_API_KEY: str = ""
    VOYAGE_API_KEY: str = ""

    # PostgreSQL
    POSTGRES_HOST: str = "db"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "tfg"
    POSTGRES_PASSWORD: str = "tfg_password"
    POSTGRES_DB: str = "tfg_validator"

    # Rules
    MAX_RULES_PER_REPO: int = 10

    # Similarity Search
    SIMILARITY_THRESHOLD: float = 0.3
    MAX_RESULTS: int = 5
    MAX_FILE_CONTENT_SIZE: int = 10000

    # Rate Limiting (embedding)
    BATCH_SIZE: int = 5
    DELAY_BETWEEN_BATCHES: float = 4.0
    EMBEDDING_RPM: int = 0

    # Rate Limiting (LLM) — shared across llm, llm_primary, llm_secondary
    LLM_RPM: int = 0 # 0 = unlimited

    # Rate Limiting (API)
    RATE_LIMIT_VALIDATE: str = "10/minute"   # Critical endpoints (validate)
    RATE_LIMIT_DEFAULT: str = "100/minute"   # All other authenticated endpoints

    # LLM Evaluation
    LLM_MODEL: str = "gemini-2.5-flash"
    LLM_MAX_CONTEXT_TOKENS: int = 900_000
    LLM_TEMPERATURE: float = 0.2
    LLM_MAX_RETRIES: int = 3
    LLM_RETRY_BASE_DELAY: float = 35.0

    # Cross-Check (dual-model consensus evaluation)
    LLM_PRIMARY_MODEL: str = "gemini-2.5-flash"
    LLM_SECONDARY_MODEL: str = "gemini-2.5-flash"

    # GitHub App
    GITHUB_APP_ID: int = 0
    GITHUB_APP_PRIVATE_KEY_PATH: str = ""   # path to the .pem file
    GITHUB_APP_SLUG: str = ""               # URL slug of the app (e.g. "validator")
    GITHUB_WEBHOOK_SECRET: str = ""         # set in the App's webhook settings
    APPROVAL_THRESHOLD: float = 0.8         # score >= threshold → approved

    # LangSmith
    LANGSMITH_API_KEY: str = ""
    LANGSMITH_ENDPOINT: str = "https://api.smith.langchain.com"
    LANGSMITH_PROJECT: str = "TFG"
    LANGSMITH_TRACING: bool = False

    # Background Worker
    WORKER_POLL_INTERVAL: int = 2
    WORKER_CONCURRENCY: int = 1       # number of parallel worker threads
    WORKER_MAX_TASK_RETRIES: int = 5  # max re-queues before marking as failed
    WORKER_RETRY_DELAY: int = 120     # seconds to wait before retrying a re-queued task

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    # Per-field validators

    @field_validator("EMBEDDING_MODEL")
    @classmethod
    def _check_embedding_model(cls, v: str) -> str:
        if v not in SUPPORTED_EMBEDDING_MODELS:
            raise ValueError(
                f"EMBEDDING_MODEL='{v}' is not valid. "
                f"Choose one of: {sorted(SUPPORTED_EMBEDDING_MODELS)}"
            )
        return v

    @field_validator("CHUNKING_STRATEGY")
    @classmethod
    def _check_chunking_strategy(cls, v: str) -> str:
        if v not in _VALID_CHUNKING_STRATEGIES:
            raise ValueError(
                f"CHUNKING_STRATEGY='{v}' is not valid. "
                f"Choose one of: {sorted(_VALID_CHUNKING_STRATEGIES)}"
            )
        return v

    @field_validator("LLM_MODEL", "LLM_PRIMARY_MODEL", "LLM_SECONDARY_MODEL")
    @classmethod
    def _check_llm_model(cls, v: str, info) -> str:
        if v not in _VALID_LLM_MODELS:
            raise ValueError(
                f"{info.field_name}='{v}' is not valid. "
                f"Choose one of: {sorted(_VALID_LLM_MODELS)}"
            )
        return v

    @field_validator("SIMILARITY_THRESHOLD", "APPROVAL_THRESHOLD")
    @classmethod
    def _check_threshold(cls, v: float, info) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError(
                f"{info.field_name}={v} must be between 0.0 and 1.0"
            )
        return v

    @field_validator("LLM_TEMPERATURE")
    @classmethod
    def _check_temperature(cls, v: float) -> float:
        if not (0.0 <= v <= 2.0):
            raise ValueError(
                f"LLM_TEMPERATURE={v} must be between 0.0 and 2.0"
            )
        return v

    @field_validator("POSTGRES_PORT")
    @classmethod
    def _check_port(cls, v: int, info) -> int:
        if not (1 <= v <= 65535):
            raise ValueError(
                f"{info.field_name}={v} must be a valid port (1–65535)"
            )
        return v

    @field_validator(
        "MAX_RULES_PER_REPO", "WORKER_POLL_INTERVAL", "WORKER_CONCURRENCY",
        "WORKER_MAX_TASK_RETRIES", "WORKER_RETRY_DELAY", "LLM_MAX_RETRIES", "BATCH_SIZE",
    )
    @classmethod
    def _check_positive_int(cls, v: int, info) -> int:
        if v < 1:
            raise ValueError(f"{info.field_name}={v} must be >= 1")
        return v

    @field_validator("MAX_RESULTS")
    @classmethod
    def _check_max_results(cls, v: int) -> int:
        if v < 1:
            raise ValueError(f"MAX_RESULTS={v} must be >= 1")
        return v

    @field_validator("LLM_MAX_CONTEXT_TOKENS")
    @classmethod
    def _check_context_tokens(cls, v: int) -> int:
        if v < 1000:
            raise ValueError(f"LLM_MAX_CONTEXT_TOKENS={v} must be >= 1000")
        return v

    # Cross-field / coherence validators

    @model_validator(mode="after")
    def _check_api_key_for_embedding_model(self) -> "Settings":
        if self.EMBEDDING_MODEL == "gemini" and not self.GOOGLE_API_KEY:
            raise ValueError(
                "EMBEDDING_MODEL='gemini' requires GOOGLE_API_KEY to be set"
            )
        if self.EMBEDDING_MODEL == "voyage" and not self.VOYAGE_API_KEY:
            raise ValueError(
                "EMBEDDING_MODEL='voyage' requires VOYAGE_API_KEY to be set"
            )
        return self

    @model_validator(mode="after")
    def _check_github_app_config(self) -> "Settings":
        has_id = self.GITHUB_APP_ID != 0
        has_key = bool(self.GITHUB_APP_PRIVATE_KEY_PATH)
        if has_id and not has_key:
            raise ValueError(
                "GITHUB_APP_ID is set but GITHUB_APP_PRIVATE_KEY_PATH is empty"
            )
        if has_key and not has_id:
            raise ValueError(
                "GITHUB_APP_PRIVATE_KEY_PATH is set but GITHUB_APP_ID is 0"
            )
        return self

    # Non-blocking warnings (called explicitly from main.py)

    def warn_if_incomplete(self) -> list[str]:
        """Return a list of warning messages for missing but non-critical config.
        Does not raise — callers should log these at WARNING level.
        """
        warnings: list[str] = []
        if not self.GITHUB_CLIENT_ID:
            warnings.append("GITHUB_CLIENT_ID is empty — OAuth login will not work")
        if not self.GITHUB_CLIENT_SECRET:
            warnings.append("GITHUB_CLIENT_SECRET is empty — OAuth login will not work")
        if self.GITHUB_APP_ID == 0:
            warnings.append(
                "GITHUB_APP_ID is 0 — GitHub App features (webhooks, PR review) are disabled"
            )
        return warnings
