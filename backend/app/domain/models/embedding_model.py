from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class EmbeddingModelSpec:
    key: str        # identifier used in EMBEDDING_MODEL config (e.g. "gemini")
    api_name: str   # model name passed to the embedding API
    dimensions: int # output vector dimensions


SUPPORTED_EMBEDDING_MODELS: Dict[str, EmbeddingModelSpec] = {
    "gemini": EmbeddingModelSpec(
        key="gemini",
        api_name="models/gemini-embedding-001",
        dimensions=3072,
    ),
    "voyage": EmbeddingModelSpec(
        key="voyage",
        api_name="voyage-code-3",
        dimensions=1024,
    ),
}
