from app.domain.ports import ChunkingPort, EmbeddingPort, VectorStorePort
from app.infrastructure.database import Database


class HealthService:
    """Checks the health of all system components."""

    def __init__(
        self,
        database: Database,
        vector_store: VectorStorePort,
        embedding: EmbeddingPort,
        chunking: ChunkingPort,
    ) -> None:
        self._database = database
        self._vector_store = vector_store
        self._embedding = embedding
        self._chunking = chunking

    def check(self) -> dict:
        postgres_ok = False
        try:
            postgres_ok = self._database.check_health()
        except Exception:
            pass

        vector_store_ok = False
        try:
            vector_store_ok = self._vector_store.check_health()
        except Exception:
            pass

        return {
            "status": "healthy" if (postgres_ok and vector_store_ok) else "degraded",
            "components": {
                "api": True,
                "postgres": postgres_ok,
                "vector_store": vector_store_ok,
            },
            "config": {
                "embedding_model": self._embedding.name,
                "chunking_strategy": self._chunking.name,
            },
        }
