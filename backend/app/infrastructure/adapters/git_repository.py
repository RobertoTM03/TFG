import shutil
import tempfile
from fnmatch import fnmatch
from pathlib import Path
from typing import List, Tuple

from git import GitCommandError, Repo
from loguru import logger

from app.domain.ports import RepositoryPort

CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".vue",
    ".sh", ".bash",
    ".yml", ".yaml", ".json", ".toml",
    ".sql",
    ".h", ".cpp", ".ino",
    ".css", ".html",
}

EXCLUDE_PATTERNS = (
    "**/node_modules/**",
    "**/package-lock.json",
    "**/.git/**",
    "**/__pycache__/**",
    "**/uv.lock",
    "**/*.pdf",
    "**/*.png",
    "**/*.jpg",
    "**/*.svg",
    "**/*.woff",
    "**/*.tex",
    "**/data/**",
)

MAX_FILE_SIZE = 1_000_000  # 1 MB


class GitRepositoryAdapter(RepositoryPort):
    """Git repository adapter for cloning and loading source files."""

    @staticmethod
    def _safe_url(url: str) -> str:
        """Strip credentials from a URL before logging or surfacing in errors."""
        return url.split("@")[-1] if "@" in url else url

    def clone(self, url: str) -> Path:
        tmp_dir = tempfile.mkdtemp(prefix="tfg_repo_")
        safe = self._safe_url(url)
        logger.info(f"Cloning {safe} into {tmp_dir}...")
        try:
            Repo.clone_from(url, tmp_dir, depth=1)
        except GitCommandError as e:
            shutil.rmtree(tmp_dir, ignore_errors=True)
            stderr = str(e.stderr).strip() if e.stderr else ""
            if (
                "could not read Username" in stderr
                or "Authentication" in stderr
            ):
                raise RuntimeError(
                    f"Cannot clone repository: {safe}. "
                    "Check the URL and ensure the repo is public."
                ) from e
            if (
                "not found" in stderr.lower()
                or "does not exist" in stderr.lower()
            ):
                raise RuntimeError(
                    f"Repository not found: {safe}. Check the URL."
                ) from e
            raise RuntimeError(
                f"Error cloning {safe}: {stderr or str(e)}"
            ) from e
        logger.info(f"Clone complete: {tmp_dir}")
        return Path(tmp_dir)

    def load_files(self, repo_path: Path) -> List[Tuple[str, str]]:
        logger.info(f"Loading code files from {repo_path}...")
        files = []

        for path in repo_path.rglob("*"):
            if not path.is_file():
                continue

            relative = str(path.relative_to(repo_path))
            norm = relative.replace("\\", "/")

            if self._should_exclude(norm, path):
                continue

            # Check extension (Dockerfile is a special case with no extension)
            if path.suffix not in CODE_EXTENSIONS and path.name != "Dockerfile":
                continue

            try:
                content = path.read_text(encoding="utf-8", errors="replace")
                files.append((norm, content))
            except Exception as e:
                logger.warning(f"Could not read {norm}: {e}")

        logger.info(f"Loaded {len(files)} files")
        return files

    def cleanup(self, repo_path: Path) -> None:
        try:
            shutil.rmtree(str(repo_path), ignore_errors=True)
            logger.info(f"Cleaned up: {repo_path}")
        except Exception as e:
            logger.warning(f"Cleanup failed: {e}")

    @staticmethod
    def _should_exclude(norm_path: str, full_path: Path) -> bool:
        if any(fnmatch(norm_path, pat) for pat in EXCLUDE_PATTERNS):
            return True
        try:
            if full_path.stat().st_size > MAX_FILE_SIZE:
                return True
        except Exception:
            pass
        return False
