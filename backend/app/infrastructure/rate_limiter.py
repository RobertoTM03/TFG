import threading
import time
from typing import List

from loguru import logger

from app.domain.ports import EmbeddingPort, LLMPort
from app.domain.models.evaluation import RuleEvaluation


class _RpmSlot:
    """Thread-safe sliding-window RPM enforcer shared across callers.

    rpm <= 0 means unlimited (slot.wait() returns immediately).
    """

    def __init__(self, rpm: int, label: str = "") -> None:
        self._rpm = rpm
        self._label = label or f"{rpm} RPM"
        self._timestamps: List[float] = []
        self._lock = threading.Lock()

    @property
    def rpm(self) -> int:
        return self._rpm

    def wait(self) -> None:
        """Block until a call slot is available, then claim it."""
        if self._rpm <= 0:
            return

        with self._lock:
            now = time.time()
            window = 60.0

            # Drop timestamps outside the rolling window
            self._timestamps = [t for t in self._timestamps if now - t < window]

            # If quota exhausted, sleep until the oldest slot frees up
            if len(self._timestamps) >= self._rpm:
                oldest = self._timestamps[0]
                wait = window - (now - oldest) + 1.0
                logger.warning(
                    f"[{self._label}] RPM limit reached ({self._rpm} RPM). "
                    f"Waiting {wait:.1f}s..."
                )
                time.sleep(wait)

                now = time.time()
                self._timestamps = [t for t in self._timestamps if now - t < window]

            self._timestamps.append(time.time())


# Embedding wrapper

class RateLimitedEmbeddings(EmbeddingPort):
    """Wraps any EmbeddingPort with RPM enforcement via a shared _RpmSlot."""

    def __init__(self, embeddings: EmbeddingPort, rpm: int) -> None:
        self._embeddings = embeddings
        self._slot = _RpmSlot(rpm, label=f"Embeddings({embeddings.name})")

    @property
    def name(self) -> str:
        return f"RateLimited({self._embeddings.name}, {self._slot.rpm} RPM)"

    @property
    def default_rpm(self) -> int:
        return self._slot.rpm

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        self._slot.wait()
        return self._embeddings.embed_documents(texts)

    def embed_query(self, text: str) -> List[float]:
        self._slot.wait()
        return self._embeddings.embed_query(text)


# LLM wrapper

class RateLimitedLLM(LLMPort):
    """Wraps any LLMPort with RPM enforcement via a shared _RpmSlot.

    Multiple instances can share the same slot so that the configured
    LLM_RPM represents the *total* quota across all model instances
    (e.g. primary + secondary in cross-check mode).
    """

    def __init__(self, llm: LLMPort, slot: _RpmSlot) -> None:
        self._llm = llm
        self._slot = slot

    @property
    def name(self) -> str:
        return f"RateLimited({self._llm.name}, {self._slot.rpm} RPM)"

    @property
    def max_context_tokens(self) -> int:
        return self._llm.max_context_tokens

    def evaluate_rule(
        self,
        rule: str,
        repomap: str,
        file_contents: List[str],
        repository_url: str,
    ) -> RuleEvaluation:
        self._slot.wait()
        return self._llm.evaluate_rule(
            rule=rule,
            repomap=repomap,
            file_contents=file_contents,
            repository_url=repository_url,
        )
