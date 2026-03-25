from typing import List

from langchain_google_genai import GoogleGenerativeAIEmbeddings

from app.config import Settings
from app.domain.ports import EmbeddingPort


class GeminiEmbeddingAdapter(EmbeddingPort):
    """Google Gemini embedding provider using native List[float] returns."""

    MODEL_NAME = "models/gemini-embedding-001"
    DEFAULT_RPM = 60

    def __init__(self, settings: Settings):
        self._provider = GoogleGenerativeAIEmbeddings(
            model=self.MODEL_NAME,
            google_api_key=settings.GOOGLE_API_KEY,
            request_options={
                "timeout": 60,
                "retry": {
                    "max_attempts": 5,
                    "initial_delay": 1.0,
                    "max_delay": 60.0,
                    "multiplier": 2.0,
                },
            },
        )

    @property
    def name(self) -> str:
        return "gemini-embedding-001"

    @property
    def default_rpm(self) -> int:
        return self.DEFAULT_RPM

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self._provider.embed_documents(texts)

    def embed_query(self, text: str) -> List[float]:
        return self._provider.embed_query(text)
