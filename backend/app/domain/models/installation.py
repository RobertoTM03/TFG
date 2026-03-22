from dataclasses import dataclass, field
from typing import List


@dataclass
class Installation:
    """A GitHub App installation on a user account or organisation."""

    installation_id: int
    account_login: str
    account_type: str        # "User" | "Organization"
    app_slug: str = ""


@dataclass
class InstalledRepo:
    """A repository accessible through a GitHub App installation."""

    installation_id: int
    full_name: str
    name: str
    private: bool
    description: str = ""
    language: str = ""
    stargazers_count: int = 0
    clone_url: str = ""
    html_url: str = ""
