import hashlib
import hmac
import json

from fastapi import APIRouter, HTTPException, Request
from loguru import logger

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


def _verify_signature(body: bytes, secret: str, sig_header: str) -> None:
    if not secret:
        logger.error("GITHUB_WEBHOOK_SECRET is not configured — rejecting webhook")
        raise HTTPException(status_code=500, detail="Webhook secret not configured")
    if not sig_header:
        raise HTTPException(status_code=403, detail="Missing webhook signature")
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig_header):
        raise HTTPException(status_code=403, detail="Invalid webhook signature")


@router.post("/github", summary="GitHub App webhook receiver")
async def github_webhook(request: Request):
    body = await request.body()
    settings = request.app.state.settings
    _verify_signature(
        body,
        settings.GITHUB_WEBHOOK_SECRET,
        request.headers.get("X-Hub-Signature-256", ""),
    )

    event_type = request.headers.get("X-GitHub-Event", "")
    payload = json.loads(body)

    # Installation lifecycle events — keep DB in sync
    if event_type == "installation":
        return await _handle_installation(payload, request)

    if event_type == "installation_repositories":
        # Repos added/removed from an existing installation — no DB action needed
        return {"ok": True}

    # Pull request events — trigger automatic validation
    if event_type == "pull_request":
        return await _handle_pull_request(payload, request)

    return {"ignored": True, "reason": f"event '{event_type}' not handled"}


async def _handle_installation(payload: dict, request: Request) -> dict:
    action = payload.get("action", "")
    db = request.app.state.database
    installation_id = payload["installation"]["id"]
    account_login = payload["installation"]["account"]["login"]

    if action in ("created", "unsuspend"):
        # Find user by their GitHub login
        sender_login = payload.get("sender", {}).get("login", "")
        user = db.get_user_by_github_login(sender_login) if sender_login else None
        if user:
            db.upsert_installation(installation_id, str(user["id"]), account_login)
            logger.info(f"Installation {installation_id} stored for user {sender_login}")

    elif action in ("deleted", "suspend"):
        db.delete_installation(installation_id)
        logger.info(f"Installation {installation_id} removed")

    return {"ok": True, "action": action}


async def _handle_pull_request(payload: dict, request: Request) -> dict:
    action = payload.get("action", "")
    if action not in ("opened", "synchronize", "reopened"):
        return {"ignored": True, "reason": f"action '{action}' not handled"}

    installation_id: int = payload["installation"]["id"]
    repo_full_name: str = payload["repository"]["full_name"]
    pr_number: int = payload["pull_request"]["number"]
    pr_head_sha: str = payload["pull_request"]["head"]["sha"]
    pr_author: str = payload["pull_request"]["user"]["login"]
    clone_url: str = payload["repository"]["clone_url"]

    db = request.app.state.database
    github_app = request.app.state.container.github_app

    # Find the repo owner (user who has rules)
    owner_user = db.get_owner_for_repo(repo_full_name)
    if not owner_user:
        return {"ignored": True, "reason": "no owner with rules found for this repository"}

    user_id = str(owner_user["id"])
    owner_login, repo_name = repo_full_name.split("/", 1)

    # Load per-repo config (falls back to defaults if not set)
    config = db.get_repo_config(user_id, repo_full_name)
    max_evals = config["max_evaluations_per_pr"] if config else 3
    enable_cross_check = config["enable_cross_check"] if config else True
    pr_evaluation_enabled = config["pr_evaluation_enabled"] if config else True

    # Precondition: PR evaluation must be enabled for this repo
    if not pr_evaluation_enabled:
        logger.info(f"PR evaluation disabled for {repo_full_name} — skipping PR #{pr_number}")
        return {"ignored": True, "reason": "pr_evaluation_enabled is False for this repository"}

    # Precondition: max evaluations per PR
    existing_count = db.count_pr_tasks(repo_full_name, pr_number)
    if existing_count >= max_evals:
        logger.info(
            f"PR #{pr_number} in {repo_full_name} already has {existing_count} evaluations "
            f"(limit: {max_evals}) — skipping"
        )
        # Keep the last commit status (success/failure) — do NOT overwrite it.
        # Just post a comment explaining the limit has been reached.
        try:
            times = "vez" if existing_count == 1 else "veces"
            github_app.post_pr_comment(
                installation_id, owner_login, repo_name, pr_number,
                f"Este PR ya ha sido evaluado {existing_count} {times} "
                f"(límite configurado: {max_evals}). "
                f"No se realizará una nueva evaluación. "
                f"El resultado de la última evaluación sigue vigente.",
            )
        except Exception as exc:
            logger.warning(f"Could not post limit comment on PR #{pr_number}: {exc}")
        return {"ignored": True, "reason": f"max_evaluations_per_pr ({max_evals}) reached for PR #{pr_number}"}

    rules, _ = db.get_rules(user_id, repo_full_name, page=1, page_size=1000)
    if not rules:
        return {"ignored": True, "reason": "no rules defined for this repository"}

    rule_texts = [r["rule_text"] for r in rules]

    # Set pending commit status immediately so the check turns yellow
    try:
        github_app.set_commit_status(
            installation_id, owner_login, repo_name, pr_head_sha,
            "pending", "Evaluación en curso…",
        )
    except Exception as exc:
        logger.warning(f"Could not set pending status for PR #{pr_number}: {exc}")

    # Store the clean clone URL — the worker will inject a fresh installation token at processing time
    task = db.create_task(
        repository_url=clone_url,
        repository_full_name=repo_full_name,
        rules=rule_texts,
        user_id=user_id,
        enable_cross_check=enable_cross_check,
        pr_number=pr_number,
        pr_head_sha=pr_head_sha,
        pr_author=pr_author,
        github_installation_id=installation_id,
    )

    logger.info(
        f"Queued auto-review task {task['id']} for {repo_full_name} PR #{pr_number} "
        f"(cross_check={enable_cross_check}, eval {existing_count + 1}/{max_evals})"
    )
    return {"task_id": str(task["id"]), "status": "queued"}
