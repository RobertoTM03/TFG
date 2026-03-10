from app.infrastructure.container import Container

class HealthService:
    """Checks the health of all system components."""

    def __init__(self, container: Container) -> None:
        self._container = container

    def check(self) -> dict:
        postgres_ok = False
        try:
            postgres_ok = self._container.database.check_health()
        except Exception:
            pass

        chroma_ok = False
        try:
            chroma_ok = self._container.vector_store.check_health()
        except Exception:
            pass

        return {
            "status": "healthy" if (postgres_ok and chroma_ok) else "degraded",
            "components": {
                "api": True,
                "postgres": postgres_ok,
                "chromadb": chroma_ok,
            },
            "config": {
                "embedding_model": self._container.embedding.name,
                "chunking_strategy": self._container.chunking.name,
            },
        }
