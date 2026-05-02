import shutil
import tempfile
import time
from fnmatch import fnmatch
from pathlib import Path
from typing import List, Optional, Tuple

from git import GitCommandError, Repo
from loguru import logger

_TRANSIENT_ERRORS = (
    "GnuTLS",
    "handshake failed",
    "TLS connection",
    "SSL_connect",
    "Connection reset",
    "Connection timed out",
    "unable to access",
    "curl",
    "recv failure",
    "OpenSSL",
)

from app.domain.ports import RepositoryPort

CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".vue",
    ".sh", ".bash",
    ".yml", ".yaml", ".json", ".toml",
    ".sql",
    ".h", ".cpp", ".ino",
    ".css", ".html",
    ".md", ".txt",
    ".java", ".go", ".rb", ".php", ".rs", ".kt",
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

    def __init__(self, max_retries: int = 3, retry_delay: float = 5.0) -> None:
        self._max_retries = max_retries
        self._retry_delay = retry_delay

    @staticmethod
    def _safe_url(url: str) -> str:
        """Strip credentials from a URL before logging or surfacing in errors."""
        return url.split("@")[-1] if "@" in url else url

    def clone(self, url: str, branch: Optional[str] = None) -> Path:
        safe = self._safe_url(url)
        branch_info = f" (branch: {branch})" if branch else ""

        for attempt in range(1, self._max_retries + 1):
            tmp_dir = tempfile.mkdtemp(prefix="tfg_repo_")
            logger.info(f"Cloning {safe}{branch_info} into {tmp_dir} (attempt {attempt}/{self._max_retries})...")
            try:
                Repo.clone_from(
                    url, tmp_dir, depth=1,
                    branch=branch if branch else None,
                    env={"GIT_TERMINAL_PROMPT": "0", "GIT_ASKPASS": "echo"},
                )
                logger.info(f"Clone complete: {tmp_dir}")
                return Path(tmp_dir)
            except GitCommandError as e:
                shutil.rmtree(tmp_dir, ignore_errors=True)
                stderr = str(e.stderr).strip() if e.stderr else ""

                if (
                    "could not read Username" in stderr
                    or "could not read Password" in stderr
                    or "Authentication failed" in stderr
                    or "authentication required" in stderr.lower()
                ):
                    raise RuntimeError(
                        f"Authentication failed cloning {safe}. "
                        "The repository may be private and the stored token may lack 'repo' scope."
                    ) from e

                if (
                    "not found" in stderr.lower()
                    or "does not exist" in stderr.lower()
                ):
                    raise RuntimeError(
                        f"Repository not found: {safe}. Check the URL."
                    ) from e

                is_transient = any(kw in stderr for kw in _TRANSIENT_ERRORS)
                if is_transient and attempt < self._max_retries:
                    logger.warning(
                        f"Transient network error cloning {safe} "
                        f"(attempt {attempt}/{self._max_retries}): {stderr[:200]}. "
                        f"Retrying in {self._retry_delay:.0f}s..."
                    )
                    time.sleep(self._retry_delay)
                    continue

                raise RuntimeError(
                    f"Error cloning {safe}: {stderr or str(e)}"
                ) from e

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
