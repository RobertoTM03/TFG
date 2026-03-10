from loguru import logger

from app.infrastructure.container import Container

class RepomapService:
    """Orchestrates repository map generation (synchronous)."""

    def __init__(self, container: Container) -> None:
        self._container = container

    def generate_repomap(self, repository_url: str) -> str:
        """Clone repo, generate repomap, cleanup."""
        repo_path = None
        try:
            repo_path = self._container.repository.clone(repository_url)
            repomap = self._container.repomap.generate(repo_path)
            return repomap
        except Exception as e:
            logger.error(f"Repomap generation failed: {e}")
            raise
        finally:
            if repo_path:
                self._container.repository.cleanup(repo_path)
