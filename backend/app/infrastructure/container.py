import threading

from app.application.services.cross_check_service import CrossCheckService
from app.config import Settings
from app.domain.ports import (
    ChunkingPort,
    EmbeddingPort,
    GitHubAppPort,
    LLMPort,
    RepomapPort,
    RepositoryPort,
    VectorStorePort,
)
from app.infrastructure.adapters.gemini_embedding import GeminiEmbeddingAdapter
from app.infrastructure.adapters.voyage_embedding import VoyageEmbeddingAdapter
from app.infrastructure.adapters.tree_sitter_chunker import TreeSitterChunkingAdapter
from app.infrastructure.adapters.tree_sitter_limited_chunker import TreeSitterLimitedChunkingAdapter
from app.infrastructure.adapters.chroma_store import ChromaVectorStoreAdapter
from app.infrastructure.adapters.git_repository import GitRepositoryAdapter
from app.infrastructure.adapters.tree_sitter_repomap import TreeSitterRepomapAdapter
from app.infrastructure.adapters.gemini_llm import GeminiLLMAdapter
from app.infrastructure.adapters.github_app_adapter import GitHubAppAdapter
from app.infrastructure.rate_limiter import RateLimitedEmbeddings
from app.infrastructure.database import Database

EMBEDDING_REGISTRY = {
    "gemini": GeminiEmbeddingAdapter,
    "voyage": VoyageEmbeddingAdapter,
}

CHUNKING_REGISTRY = {
    "tree-sitter": lambda: TreeSitterChunkingAdapter(
        include_methods=True,
    ),
    "tree-sitter-limited": lambda: TreeSitterLimitedChunkingAdapter(
        include_methods=True,
        max_chunk_size=2048,
        chunk_overlap=256,
    ),
}


class Container:
    """DI Container - resolves and caches all infrastructure instances."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._lock = threading.Lock()
        self._embedding: EmbeddingPort | None = None
        self._chunking: ChunkingPort | None = None
        self._vector_store: VectorStorePort | None = None
        self._repository: RepositoryPort | None = None
        self._repomap: RepomapPort | None = None
        self._github_app: GitHubAppPort | None = None
        self._llm: LLMPort | None = None
        self._llm_primary: LLMPort | None = None
        self._llm_secondary: LLMPort | None = None
        self._cross_check_service: CrossCheckService | None = None
        self._database: Database | None = None

    # Embedding

    @property
    def embedding(self) -> EmbeddingPort:
        if self._embedding is None:
            with self._lock:
                if self._embedding is None:
                    key = self._settings.EMBEDDING_MODEL.lower()
                    cls = EMBEDDING_REGISTRY.get(key)
                    if cls is None:
                        available = ", ".join(EMBEDDING_REGISTRY.keys())
                        raise ValueError(
                            f"Unknown embedding model '{key}'. Available: {available}"
                        )
                    self._embedding = cls(self._settings)
        return self._embedding

    # Chunking

    @property
    def chunking(self) -> ChunkingPort:
        if self._chunking is None:
            with self._lock:
                if self._chunking is None:
                    key = self._settings.CHUNKING_STRATEGY.lower()
                    factory = CHUNKING_REGISTRY.get(key)
                    if factory is None:
                        available = ", ".join(CHUNKING_REGISTRY.keys())
                        raise ValueError(
                            f"Unknown chunking strategy '{key}'. Available: {available}"
                        )
                    self._chunking = factory()
        return self._chunking

    # Vector Store

    @property
    def vector_store(self) -> VectorStorePort:
        if self._vector_store is None:
            with self._lock:
                if self._vector_store is None:
                    raw_embeddings = self.embedding
                    rpm = (
                        self._settings.EMBEDDING_RPM
                        if self._settings.EMBEDDING_RPM > 0
                        else self.embedding.default_rpm
                    )
                    rate_limited = RateLimitedEmbeddings(raw_embeddings, rpm)
                    self._vector_store = ChromaVectorStoreAdapter(
                        host=self._settings.CHROMA_HOST,
                        port=self._settings.CHROMA_PORT,
                        embeddings=rate_limited,
                        batch_size=self._settings.BATCH_SIZE,
                        delay_between_batches=self._settings.DELAY_BETWEEN_BATCHES,
                    )
        return self._vector_store

    # Repository

    @property
    def repository(self) -> RepositoryPort:
        if self._repository is None:
            with self._lock:
                if self._repository is None:
                    self._repository = GitRepositoryAdapter()
        return self._repository

    # Repomap

    @property
    def repomap(self) -> RepomapPort:
        if self._repomap is None:
            with self._lock:
                if self._repomap is None:
                    self._repomap = TreeSitterRepomapAdapter()
        return self._repomap

    # LLM

    @property
    def llm(self) -> LLMPort:
        if self._llm is None:
            with self._lock:
                if self._llm is None:
                    self._llm = GeminiLLMAdapter(
                        settings=self._settings,
                        model_name=self._settings.LLM_MODEL,
                        max_context_tokens=self._settings.LLM_MAX_CONTEXT_TOKENS,
                        temperature=self._settings.LLM_TEMPERATURE,
                        max_retries=self._settings.LLM_MAX_RETRIES,
                        retry_base_delay=self._settings.LLM_RETRY_BASE_DELAY,
                    )
        return self._llm

    # Primary LLM (used when ENABLE_CROSS_CHECK=True)

    @property
    def llm_primary(self) -> LLMPort:
        if self._llm_primary is None:
            with self._lock:
                if self._llm_primary is None:
                    self._llm_primary = GeminiLLMAdapter(
                        settings=self._settings,
                        model_name=self._settings.LLM_PRIMARY_MODEL,
                        max_context_tokens=self._settings.LLM_MAX_CONTEXT_TOKENS,
                        temperature=self._settings.LLM_TEMPERATURE,
                        max_retries=self._settings.LLM_MAX_RETRIES,
                        retry_base_delay=self._settings.LLM_RETRY_BASE_DELAY,
                    )
        return self._llm_primary

    # Secondary LLM (used when ENABLE_CROSS_CHECK=True)

    @property
    def llm_secondary(self) -> LLMPort:
        if self._llm_secondary is None:
            with self._lock:
                if self._llm_secondary is None:
                    self._llm_secondary = GeminiLLMAdapter(
                        settings=self._settings,
                        model_name=self._settings.LLM_SECONDARY_MODEL,
                        max_context_tokens=self._settings.LLM_MAX_CONTEXT_TOKENS,
                        temperature=self._settings.LLM_TEMPERATURE,
                        max_retries=self._settings.LLM_MAX_RETRIES,
                        retry_base_delay=self._settings.LLM_RETRY_BASE_DELAY,
                    )
        return self._llm_secondary

    # Cross-Check Service

    @property
    def cross_check_service(self) -> CrossCheckService:
        if self._cross_check_service is None:
            with self._lock:
                if self._cross_check_service is None:
                    self._cross_check_service = CrossCheckService()
        return self._cross_check_service

    # GitHub App

    @property
    def github_app(self) -> GitHubAppPort:
        if self._github_app is None:
            with self._lock:
                if self._github_app is None:
                    key_path = self._settings.GITHUB_APP_PRIVATE_KEY_PATH
                    private_key = ""
                    if key_path:
                        try:
                            with open(key_path) as f:
                                private_key = f.read()
                        except Exception as exc:
                            raise RuntimeError(
                                f"Cannot read GitHub App private key from '{key_path}': {exc}"
                            )
                    self._github_app = GitHubAppAdapter(
                        app_id=self._settings.GITHUB_APP_ID,
                        private_key_pem=private_key,
                        webhook_secret=self._settings.GITHUB_WEBHOOK_SECRET,
                    )
        return self._github_app

    # Database

    @property
    def database(self) -> Database:
        if self._database is None:
            with self._lock:
                if self._database is None:
                    self._database = Database(
                        host=self._settings.POSTGRES_HOST,
                        port=self._settings.POSTGRES_PORT,
                        user=self._settings.POSTGRES_USER,
                        password=self._settings.POSTGRES_PASSWORD,
                        dbname=self._settings.POSTGRES_DB,
                    )
        return self._database
