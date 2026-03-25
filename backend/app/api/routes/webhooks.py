import hashlib
import hmac
import json

from fastapi import APIRouter, HTTPException, Request
from loguru import logger

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


def _verify_signature(body: bytes, secret: str, sig_header: str) -> None:
    if not secret:
        logger.warning("GITHUB_WEBHOOK_SECRET not set — skipping signature verification")
        return
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
    clone_url: str = payload["repository"]["clone_url"]

    db = request.app.state.database
    github_app = request.app.state.container.github_app

    # Find the repo owner (user who has rules)
    owner_user = db.get_owner_for_repo(repo_full_name)
    if not owner_user:
        return {"ignored": True, "reason": "no owner with rules found for this repository"}

    rules, _ = db.get_rules(str(owner_user["id"]), repo_full_name, page=1, page_size=1000)
    if not rules:
        return {"ignored": True, "reason": "no rules defined for this repository"}

    rule_texts = [r["rule_text"] for r in rules]
    owner_login, repo_name = repo_full_name.split("/", 1)

    # Set pending commit status immediately
    try:
        github_app.set_commit_status(
            installation_id, owner_login, repo_name, pr_head_sha,
            "pending", "Automated validation in progress…",
        )
    except Exception as exc:
        logger.warning(f"Could not set pending status for PR #{pr_number}: {exc}")

    # Store the clean clone URL — the worker will inject a fresh installation token at processing time
    task = db.create_task(
        repository_url=clone_url,
        repository_full_name=repo_full_name,
        rules=rule_texts,
        user_id=str(owner_user["id"]),
        enable_cross_check=True,
        pr_number=pr_number,
        pr_head_sha=pr_head_sha,
        github_installation_id=installation_id,
    )

    logger.info(
        f"Queued auto-review task {task['id']} for {repo_full_name} PR #{pr_number}"
    )
    return {"task_id": str(task["id"]), "status": "queued"}
