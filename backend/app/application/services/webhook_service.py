from loguru import logger

from app.domain.ports.github_app import GitHubAppPort
from app.domain.ports.installation_repository import InstallationRepositoryPort
from app.domain.ports.repo_config_repository import RepoConfigRepositoryPort
from app.domain.ports.rule_repository import RuleRepositoryPort
from app.domain.ports.task_repository import TaskRepositoryPort
from app.domain.ports.user_repository import UserRepositoryPort


class WebhookService:
    def __init__(
        self,
        user_repo: UserRepositoryPort,
        installation_repo: InstallationRepositoryPort,
        task_repo: TaskRepositoryPort,
        rule_repo: RuleRepositoryPort,
        repo_config_repo: RepoConfigRepositoryPort,
        github_app: GitHubAppPort,
    ) -> None:
        self._user_repo = user_repo
        self._installation_repo = installation_repo
        self._task_repo = task_repo
        self._rule_repo = rule_repo
        self._repo_config_repo = repo_config_repo
        self._github_app = github_app

    def handle_installation(self, payload: dict) -> dict:
        action = payload.get("action", "")
        installation_id = payload["installation"]["id"]
        account_login = payload["installation"]["account"]["login"]

        if action in ("created", "unsuspend"):
            sender_login = payload.get("sender", {}).get("login", "")
            user = self._user_repo.get_user_by_github_login(sender_login) if sender_login else None
            if user:
                self._installation_repo.upsert_installation(
                    installation_id, str(user["id"]), account_login,
                )
                logger.info(f"Installation {installation_id} stored for user {sender_login}")

        elif action in ("deleted", "suspend"):
            self._installation_repo.delete_installation(installation_id)
            logger.info(f"Installation {installation_id} removed")

        return {"ok": True, "action": action}

    def handle_pull_request(self, payload: dict) -> dict:
        action = payload.get("action", "")
        if action not in ("opened", "synchronize", "reopened"):
            return {"ignored": True, "reason": f"action '{action}' not handled"}

        installation_id: int = payload["installation"]["id"]
        repo_full_name: str = payload["repository"]["full_name"]
        pr_number: int = payload["pull_request"]["number"]
        pr_head_sha: str = payload["pull_request"]["head"]["sha"]
        pr_head_ref: str = payload["pull_request"]["head"]["ref"]
        pr_author: str = payload["pull_request"]["user"]["login"]
        clone_url: str = payload["repository"]["clone_url"]

        owner_user = self._installation_repo.get_owner_for_repo(repo_full_name)
        if not owner_user:
            return {"ignored": True, "reason": "no owner with rules found for this repository"}

        user_id = str(owner_user["id"])
        owner_login, repo_name = repo_full_name.split("/", 1)

        config = self._repo_config_repo.get_repo_config(user_id, repo_full_name)
        max_evals = config["max_evaluations_per_pr"] if config else 3
        enable_cross_check = config["enable_cross_check"] if config else True
        pr_evaluation_enabled = config["pr_evaluation_enabled"] if config else True

        if not pr_evaluation_enabled:
            logger.info(f"PR evaluation disabled for {repo_full_name} — skipping PR #{pr_number}")
            return {"ignored": True, "reason": "pr_evaluation_enabled is False for this repository"}

        existing_count = self._task_repo.count_pr_tasks(repo_full_name, pr_number)
        if existing_count >= max_evals:
            logger.info(
                f"PR #{pr_number} in {repo_full_name} already has {existing_count} evaluations "
                f"(limit: {max_evals}) — skipping"
            )
            try:
                times = "vez" if existing_count == 1 else "veces"
                self._github_app.post_pr_comment(
                    installation_id, owner_login, repo_name, pr_number,
                    f"Este PR ya ha sido evaluado {existing_count} {times} "
                    f"(límite configurado: {max_evals}). "
                    f"No se realizará una nueva evaluación. "
                    f"El resultado de la última evaluación sigue vigente.",
                )
            except Exception as exc:
                logger.warning(f"Could not post limit comment on PR #{pr_number}: {exc}")
            return {"ignored": True, "reason": f"max_evaluations_per_pr ({max_evals}) reached for PR #{pr_number}"}

        rules, _ = self._rule_repo.get_rules(user_id, repo_full_name, page=1, page_size=1000)
        if not rules:
            return {"ignored": True, "reason": "no rules defined for this repository"}

        rule_texts = [r["rule_text"] for r in rules if r.get("enabled", True)]

        try:
            self._github_app.set_commit_status(
                installation_id, owner_login, repo_name, pr_head_sha,
                "pending", "Evaluación en curso…",
            )
        except Exception as exc:
            logger.warning(f"Could not set pending status for PR #{pr_number}: {exc}")

        task = self._task_repo.create_task(
            repository_url=clone_url,
            repository_full_name=repo_full_name,
            rules=rule_texts,
            user_id=user_id,
            enable_cross_check=enable_cross_check,
            pr_number=pr_number,
            pr_head_sha=pr_head_sha,
            pr_head_ref=pr_head_ref,
            pr_author=pr_author,
            github_installation_id=installation_id,
        )

        logger.info(
            f"Queued auto-review task {task['id']} for {repo_full_name} PR #{pr_number} "
            f"(cross_check={enable_cross_check}, eval {existing_count + 1}/{max_evals})"
        )
        return {"task_id": str(task["id"]), "status": "queued"}
