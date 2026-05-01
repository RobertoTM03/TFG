from app.domain.ports import ChunkingPort, EmbeddingPort, HealthCheckPort, VectorStorePort


class HealthService:
    """Checks the health of all system components."""

    def __init__(
        self,
        health_check: HealthCheckPort,
        vector_store: VectorStorePort,
        embedding: EmbeddingPort,
        chunking: ChunkingPort,
    ) -> None:
        self._health_check = health_check
        self._vector_store = vector_store
        self._embedding = embedding
        self._chunking = chunking

    def check(self) -> dict:
        postgres_ok = False
        try:
            postgres_ok = self._health_check.check_health()
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
