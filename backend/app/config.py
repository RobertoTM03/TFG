from pydantic_settings import BaseSettings


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

    # ChromaDB
    CHROMA_HOST: str = "chromadb"
    CHROMA_PORT: int = 8000

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

    # Rate Limiting 
    BATCH_SIZE: int = 5
    DELAY_BETWEEN_BATCHES: float = 4.0
    EMBEDDING_RPM: int = 0

    # LLM Evaluation
    LLM_MODEL: str = "gemini-2.5-flash"
    LLM_MAX_CONTEXT_TOKENS: int = 900_000
    LLM_TEMPERATURE: float = 0.2
    LLM_MAX_RETRIES: int = 3
    LLM_RETRY_BASE_DELAY: float = 35.0

    # Cross-Check (dual-model consensus evaluation)
    ENABLE_CROSS_CHECK: bool = True
    LLM_PRIMARY_MODEL: str = "gemini-2.5-flash"   # gemini-2.5-flash | gemini-2.5-pro | gemini-2.0-flash | gemini-3.1-flash-lite-preview
    LLM_SECONDARY_MODEL: str = "gemini-2.0-flash"  # gemini-2.5-flash | gemini-2.5-pro | gemini-2.0-flash | gemini-3.1-flash-lite-preview

    # GitHub App
    GITHUB_APP_ID: int = 0
    GITHUB_APP_PRIVATE_KEY_PATH: str = ""   # path to the .pem file
    GITHUB_APP_SLUG: str = ""               # URL slug of the app (e.g. "validator")
    GITHUB_WEBHOOK_SECRET: str = ""         # set in the App's webhook settings
    APPROVAL_THRESHOLD: float = 0.8         # score >= threshold → approved

    # Background Worker
    WORKER_POLL_INTERVAL: int = 2

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}
