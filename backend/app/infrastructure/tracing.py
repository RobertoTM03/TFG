import os
from contextlib import contextmanager
from typing import Dict, Generator, List, Optional

from app.domain.models.chunk import CodeChunk, SearchResult
from app.domain.models.evaluation import RuleEvaluation
from app.domain.ports import LLMPort, VectorStorePort

# SDK availability guard

try:
    from langsmith import traceable
    from langsmith import trace as _ls_trace
    _LANGSMITH_AVAILABLE = True
except ImportError:
    _LANGSMITH_AVAILABLE = False

# Setup

def setup_langsmith(api_key: str, endpoint: str, project: str, enabled: bool) -> None:
    """Configure LangSmith SDK via environment variables at startup."""
    if not enabled or not api_key:
        os.environ["LANGCHAIN_TRACING_V2"] = "false"
        return
    os.environ["LANGSMITH_API_KEY"] = api_key
    os.environ["LANGCHAIN_API_KEY"] = api_key       # alias used by older SDK versions
    os.environ["LANGSMITH_ENDPOINT"] = endpoint
    os.environ["LANGCHAIN_ENDPOINT"] = endpoint     # alias used by older SDK versions
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_PROJECT"] = project

# Module-level @traceable functions

if _LANGSMITH_AVAILABLE:
    @traceable(run_type="llm", name="llm_evaluate_rule")
    def _traced_evaluate_rule(
        rule: str,
        repomap: str,
        file_contents: List[str],
        repository_url: str,
        delegate: LLMPort,
    ) -> RuleEvaluation:
        return delegate.evaluate_rule(rule, repomap, file_contents, repository_url)

    @traceable(run_type="retriever", name="vector_store_similarity_search")
    def _traced_similarity_search(
        query: str,
        collection_name: str,
        threshold: float,
        max_results: int,
        filter_metadata: Optional[Dict],
        pr_branch: Optional[str],
        delegate: VectorStorePort,
    ) -> List[SearchResult]:
        return delegate.similarity_search(
            query, collection_name, threshold, max_results, filter_metadata, pr_branch,
        )
else:
    def _traced_evaluate_rule(rule, repomap, file_contents, repository_url, delegate):  # type: ignore[misc]
        return delegate.evaluate_rule(rule, repomap, file_contents, repository_url)

    def _traced_similarity_search(query, collection_name, threshold, max_results, filter_metadata, pr_branch, delegate):  # type: ignore[misc]
        return delegate.similarity_search(
            query, collection_name, threshold, max_results, filter_metadata, pr_branch,
        )

# Parent-trace context manager

@contextmanager
def validation_trace(
    repository_url: str,
    rules: List[str],
    enabled: bool = True,
) -> Generator:
    """Context manager that creates a LangSmith parent trace for a full validation run."""
    if not _LANGSMITH_AVAILABLE or not enabled:
        yield None
        return

    with _ls_trace(
        name="rag_validation",
        run_type="chain",
        inputs={
            "repository_url": repository_url,
            "rules": rules,
            "num_rules": len(rules),
        },
    ) as run:
        yield run

# Wrapper: LLMPort

class TracedLLMAdapter(LLMPort):
    """Transparent wrapper around any LLMPort implementation."""

    def __init__(self, delegate: LLMPort) -> None:
        self._delegate = delegate

    @property
    def name(self) -> str:
        return self._delegate.name

    @property
    def max_context_tokens(self) -> int:
        return self._delegate.max_context_tokens

    def evaluate_rule(
        self,
        rule: str,
        repomap: str,
        file_contents: List[str],
        repository_url: str,
    ) -> RuleEvaluation:
        return _traced_evaluate_rule(
            rule, repomap, file_contents, repository_url, delegate=self._delegate,
        )

# Wrapper: VectorStorePort

class TracedVectorStoreAdapter(VectorStorePort):
    """Transparent wrapper around any VectorStorePort implementation."""

    def __init__(self, delegate: VectorStorePort) -> None:
        self._delegate = delegate

    # Traced method

    def similarity_search(
        self,
        query: str,
        collection_name: str,
        threshold: float = 0.3,
        max_results: int = 5,
        filter_metadata: Optional[Dict] = None,
        pr_branch: Optional[str] = None,
    ) -> List[SearchResult]:
        return _traced_similarity_search(
            query, collection_name, threshold, max_results, filter_metadata, pr_branch, delegate=self._delegate,
        )

    def index_documents(self, chunks: List[CodeChunk], collection_name: str, branch: str = '') -> int:
        return self._delegate.index_documents(chunks, collection_name, branch)

    def collection_exists(self, collection_name: str) -> bool:
        return self._delegate.collection_exists(collection_name)

    def delete_collection(self, collection_name: str) -> None:
        return self._delegate.delete_collection(collection_name)

    def delete_by_sources(self, collection_name: str, source_paths: List[str], branch: str = '') -> int:
        return self._delegate.delete_by_sources(collection_name, source_paths, branch)

    def delete_branch(self, collection_name: str, branch: str) -> int:
        return self._delegate.delete_branch(collection_name, branch)

    def collection_count(self, collection_name: str) -> int:
        return self._delegate.collection_count(collection_name)

    def check_health(self) -> bool:
        return self._delegate.check_health()
