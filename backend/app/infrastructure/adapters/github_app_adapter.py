import time
from datetime import datetime
from typing import List

import httpx
import jwt
from loguru import logger

from app.domain.models.installation import Installation, InstalledRepo
from app.domain.ports.github_app import GitHubAppPort

_GITHUB_API = "https://api.github.com"
_ACCEPT = "application/vnd.github+json"
_API_VERSION = "2022-11-28"


class GitHubAppAdapter(GitHubAppPort):
    """GitHub App adapter: authenticates as the App (JWT) or as an installation."""

    def __init__(self, app_id: int, private_key_pem: str, webhook_secret: str = "") -> None:
        self._app_id = app_id
        self._private_key = private_key_pem
        self._webhook_secret = webhook_secret
        # Cache installation tokens: {installation_id: (token, expires_at)}
        self._token_cache: dict[int, tuple[str, float]] = {}

    # JWT (App-level auth)
    def _make_jwt(self) -> str:
        now = int(time.time())
        payload = {"iat": now - 60, "exp": now + 540, "iss": str(self._app_id)}
        return jwt.encode(payload, self._private_key, algorithm="RS256")

    def _app_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._make_jwt()}",
            "Accept": _ACCEPT,
            "X-GitHub-Api-Version": _API_VERSION,
        }

    # Installation token (cached, refreshed before expiry)
    def _get_installation_token(self, installation_id: int) -> str:
        cached = self._token_cache.get(installation_id)
        if cached and cached[1] > time.time() + 60:
            return cached[0]

        url = f"{_GITHUB_API}/app/installations/{installation_id}/access_tokens"
        with httpx.Client(timeout=10) as client:
            r = client.post(url, headers=self._app_headers())
        if r.status_code not in (200, 201):
            raise RuntimeError(
                f"Could not get installation token for {installation_id}: "
                f"{r.status_code} {r.text}"
            )
        data = r.json()
        token = data["token"]
        
        expires_at = datetime.fromisoformat(data["expires_at"]).timestamp()
        self._token_cache[installation_id] = (token, expires_at)
        return token

    def get_installation_token(self, installation_id: int) -> str:
        return self._get_installation_token(installation_id)

    def get_installation_id_for_repo(self, owner: str, repo: str) -> int | None:
        """Ask GitHub which installation covers a given repository (JWT-authenticated)."""
        url = f"{_GITHUB_API}/repos/{owner}/{repo}/installation"
        with httpx.Client(timeout=10) as client:
            r = client.get(url, headers=self._app_headers())
        if r.status_code == 200:
            return r.json().get("id")
        logger.warning(f"get_installation_id_for_repo({owner}/{repo}) returned {r.status_code}")
        return None

    def _installation_headers(self, installation_id: int) -> dict:
        return {
            "Authorization": f"Bearer {self._get_installation_token(installation_id)}",
            "Accept": _ACCEPT,
            "X-GitHub-Api-Version": _API_VERSION,
        }

    def _user_headers(self, user_token: str) -> dict:
        return {
            "Authorization": f"Bearer {user_token}",
            "Accept": _ACCEPT,
            "X-GitHub-Api-Version": _API_VERSION,
        }

    # GitHubAppPort — user-facing queries
    def get_user_installations(self, user_token: str) -> List[Installation]:
        url = f"{_GITHUB_API}/user/installations"
        installations: List[Installation] = []
        page = 1
        with httpx.Client(timeout=10) as client:
            while True:
                r = client.get(
                    url,
                    headers=self._user_headers(user_token),
                    params={"per_page": 100, "page": page},
                )
                if not r.is_success:
                    logger.warning(f"get_user_installations returned {r.status_code}")
                    break
                data = r.json()
                for inst in data.get("installations", []):
                    installations.append(Installation(
                        installation_id=inst["id"],
                        account_login=inst["account"]["login"],
                        account_type=inst["account"]["type"],
                        app_slug=inst.get("app_slug", ""),
                    ))
                if len(data.get("installations", [])) < 100:
                    break
                page += 1
        return installations

    def get_installation_repos(
        self, user_token: str, installation_id: int
    ) -> List[InstalledRepo]:
        url = f"{_GITHUB_API}/user/installations/{installation_id}/repositories"
        repos: List[InstalledRepo] = []
        page = 1
        with httpx.Client(timeout=10) as client:
            while True:
                r = client.get(
                    url,
                    headers=self._user_headers(user_token),
                    params={"per_page": 100, "page": page},
                )
                if not r.is_success:
                    logger.warning(
                        f"get_installation_repos({installation_id}) returned {r.status_code}"
                    )
                    break
                data = r.json()
                for repo in data.get("repositories", []):
                    repos.append(InstalledRepo(
                        installation_id=installation_id,
                        full_name=repo["full_name"],
                        name=repo["name"],
                        private=repo.get("private", False),
                        description=repo.get("description") or "",
                        language=repo.get("language") or "",
                        stargazers_count=repo.get("stargazers_count", 0),
                        clone_url=repo.get("clone_url", ""),
                        html_url=repo.get("html_url", ""),
                    ))
                if len(data.get("repositories", [])) < 100:
                    break
                page += 1
        return repos

    # GitHubAppPort — bot actions
    def post_pr_comment(
        self,
        installation_id: int,
        owner: str,
        repo: str,
        pr_number: int,
        body: str,
    ) -> None:
        url = f"{_GITHUB_API}/repos/{owner}/{repo}/issues/{pr_number}/comments"
        with httpx.Client(timeout=15) as client:
            r = client.post(
                url,
                json={"body": body},
                headers=self._installation_headers(installation_id),
            )
        if r.status_code not in (200, 201):
            logger.warning(f"post_pr_comment returned {r.status_code}: {r.text}")

    def set_commit_status(
        self,
        installation_id: int,
        owner: str,
        repo: str,
        sha: str,
        state: str,
        description: str,
    ) -> None:
        url = f"{_GITHUB_API}/repos/{owner}/{repo}/statuses/{sha}"
        payload = {
            "state": state,
            "description": description[:140],
            "context": "tfg-validator",
        }
        with httpx.Client(timeout=10) as client:
            r = client.post(
                url,
                json=payload,
                headers=self._installation_headers(installation_id),
            )
        if r.status_code not in (200, 201):
            logger.warning(f"set_commit_status returned {r.status_code}: {r.text}")

    # Score & comment helpers (moved from github_review_adapter)
    def calculate_score(self, result_json: dict) -> float:
        validations = result_json.get("validations", [])
        if not validations:
            return 0.0
        earned = 0.0
        for v in validations:
            ev = v.get("evaluation") or {}
            verdict = ev.get("verdict")
            if verdict == "pass":
                earned += 1.0
            elif verdict == "partial":
                earned += 0.5
        return earned / len(validations)

    def build_comment(
        self,
        score: float,
        result_json: dict,
        threshold: float,
        eval_number: int = 1,
    ) -> str:
        validations = result_json.get("validations", [])
        total = len(validations)
        pct = int(score * 100)

        # Classify rules
        fails, partials, passes = [], [], []
        for v in validations:
            rule = v.get("rule", "")
            cc = v.get("cross_check")
            ev = v.get("evaluation") or {}
            if cc:
                verdict = cc.get("primary_verdict", "unknown")
                explanation = cc.get("primary_explanation", "")
            else:
                verdict = ev.get("verdict", "unknown")
                explanation = ev.get("explanation", "")
            first = explanation.split(". ")[0].strip() if explanation else ""
            if verdict == "pass":
                passes.append(rule)
            elif verdict == "partial":
                partials.append((rule, first))
            else:
                fails.append((rule, first))

        approved = score >= threshold
        lines = []

        # Header
        result_label = "APROBADO" if approved else "NO APROBADO"
        lines.append(f"## Informe de evaluación #{eval_number}")
        lines.append("")
        lines.append(f"**Resultado: {result_label}** — {pct}% de normas superadas (mínimo: {int(threshold * 100)}%)")
        lines.append("")
        lines.append("---")

        def _section(title, items, open_tag):
            section = []
            section.append("")
            section.append(f"#### {title}")
            section.append("")
            for i, (rule, explanation) in enumerate(items, start=1):
                tag = "<details open>" if open_tag else "<details>"
                section.append(tag)
                section.append(f"<summary>{rule}</summary>")
                section.append("")
                section.append(explanation if explanation else "Sin observaciones.")
                section.append("")
                section.append("</details>")
                section.append("")
            section.append("---")
            return section

        # Numerar globalmente
        idx = 1
        numbered_fails    = []
        numbered_partials = []
        numbered_passes   = []

        for rule, explanation in fails:
            numbered_fails.append((f"{idx}. {rule}", explanation))
            idx += 1
        for rule, explanation in partials:
            numbered_partials.append((f"{idx}. {rule}", explanation))
            idx += 1
        for rule in passes:
            numbered_passes.append((f"{idx}. {rule}", ""))
            idx += 1

        if numbered_fails:
            lines += _section("No cumplido", numbered_fails, open_tag=True)
        if numbered_partials:
            lines += _section("Pendiente de revisión", numbered_partials, open_tag=False)
        if numbered_passes:
            lines += _section("Superado", numbered_passes, open_tag=False)

        lines.append("_Generado automáticamente_")
        return "\n".join(lines)
