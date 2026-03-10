import threading
import time
from typing import List

from loguru import logger

from app.domain.ports import EmbeddingPort


class RateLimitedEmbeddings(EmbeddingPort):
    """Wraps any EmbeddingPort with strict RPM enforcement."""

    def __init__(self, embeddings: EmbeddingPort, rpm: int) -> None:
        self._embeddings = embeddings
        self._rpm = rpm
        self._call_timestamps: List[float] = []
        self._lock = threading.Lock()

    @property
    def name(self) -> str:
        return f"RateLimited({self._embeddings.name}, {self._rpm} RPM)"

    @property
    def default_rpm(self) -> int:
        return self._rpm

    def _wait_for_slot(self) -> None:
        if self._rpm <= 0:
            return

        with self._lock:
            now = time.time()
            window = 60.0

            # Remove timestamps older than 60 seconds
            self._call_timestamps = [
                t for t in self._call_timestamps if now - t < window
            ]

            # If we've hit the limit, wait until the oldest slot frees up
            if len(self._call_timestamps) >= self._rpm:
                oldest = self._call_timestamps[0]
                wait = window - (now - oldest) + 1.0
                logger.warning(
                    f"RPM limit reached ({self._rpm} RPM). "
                    f"Waiting {wait:.1f}s..."
                )
                time.sleep(wait)
                
                # Update timestamps after sleeping
                now = time.time()
                self._call_timestamps = [
                    t for t in self._call_timestamps if now - t < window
                ]

            self._call_timestamps.append(time.time())

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        self._wait_for_slot()
        return self._embeddings.embed_documents(texts)

    def embed_query(self, text: str) -> List[float]:
        self._wait_for_slot()
        return self._embeddings.embed_query(text)
