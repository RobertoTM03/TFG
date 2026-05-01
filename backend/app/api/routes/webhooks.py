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

    webhook_service = request.app.state.container.webhook_service

    if event_type == "installation":
        return webhook_service.handle_installation(payload)

    if event_type == "installation_repositories":
        return {"ok": True}

    if event_type == "pull_request":
        return webhook_service.handle_pull_request(payload)

    return {"ignored": True, "reason": f"event '{event_type}' not handled"}
