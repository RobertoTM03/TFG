from abc import ABC, abstractmethod
from typing import List, Optional

from app.domain.models.installation import Installation, InstalledRepo


class GitHubAppPort(ABC):
    """Port for GitHub App operations (installation management and bot interactions)."""

    # App-level queries (authenticate as the GitHub App via JWT)
    @abstractmethod
    def get_installation_token(self, installation_id: int) -> str:
        """Return a short-lived installation access token for the given installation."""
        ...

    @abstractmethod
    def get_installation_id_for_repo(self, owner: str, repo: str) -> Optional[int]:
        """Return the installation ID that covers the given repository, or None."""
        ...

    # User-facing queries (use the user's OAuth token)
    @abstractmethod
    def get_user_installations(self, user_token: str) -> List[Installation]:
        """Return all installations the authenticated user can access."""
        ...

    @abstractmethod
    def get_installation_repos(
        self, user_token: str, installation_id: int
    ) -> List[InstalledRepo]:
        """Return repositories accessible under a specific installation."""
        ...

    # Bot actions (authenticate as the App using installation_id)
    @abstractmethod
    def post_pr_comment(
        self,
        installation_id: int,
        owner: str,
        repo: str,
        pr_number: int,
        body: str,
    ) -> None:
        """Post a comment on a pull request as the bot."""
        ...

    @abstractmethod
    def set_commit_status(
        self,
        installation_id: int,
        owner: str,
        repo: str,
        sha: str,
        state: str,        # "pending" | "success" | "failure" | "error"
        description: str,
    ) -> None:
        """Update the commit status shown in the PR checks area."""
        ...

    # Review helpers
    @abstractmethod
    def calculate_score(self, result_json: dict) -> float:
        """Compute a 0-1 score from a completed validation result."""
        ...

    @abstractmethod
    def build_comment(self, score: float, result_json: dict, threshold: float) -> str:
        """Build the Markdown comment body for a PR review."""
        ...
