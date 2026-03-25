from typing import List

from langchain_voyageai import VoyageAIEmbeddings

from app.config import Settings
from app.domain.ports import EmbeddingPort


class VoyageEmbeddingAdapter(EmbeddingPort):
    """Voyage AI code embedding provider using native List[float] returns."""

    MODEL_NAME = "voyage-code-3"
    DEFAULT_RPM = 3

    def __init__(self, settings: Settings):
        self._provider = VoyageAIEmbeddings(
            model=self.MODEL_NAME,
            voyage_api_key=settings.VOYAGE_API_KEY,
        )

    @property
    def name(self) -> str:
        return "voyage-code-3"

    @property
    def default_rpm(self) -> int:
        return self.DEFAULT_RPM

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self._provider.embed_documents(texts)

    def embed_query(self, text: str) -> List[float]:
        return self._provider.embed_query(text)
