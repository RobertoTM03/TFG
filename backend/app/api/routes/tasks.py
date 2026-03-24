import json

from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket

from app.api.dependencies import get_current_user
from app.api.schemas import (
    CrossCheckResponse,
    FileMatchResponse,
    RuleEvaluationResponse,
    RuleValidationResponse,
    TaskCreatedResponse,
    TaskDetailResponse,
    TaskResultResponse,
    TaskSummaryResponse,
)

router = APIRouter(tags=["Tasks"])


# Authenticated: start validation with rules from the database

@router.post(
    "/api/repos/{owner}/{repo}/validate",
    status_code=202,
    summary="Validate a repository against its stored rules",
    response_model=TaskCreatedResponse,
)
async def validate_repo(
    owner: str,
    repo: str,
    request: Request,
    cross_check: bool = True,
    user: dict = Depends(get_current_user),
):
    """Read the user's rules for this repository and launch a
    background validation task. Returns immediately with a task id."""
    db = request.app.state.database
    full_name = f"{owner}/{repo}"

    rules = db.get_rules(str(user["id"]), full_name)
    if not rules:
        raise HTTPException(
            status_code=400,
            detail="No rules defined for this repository",
        )

    rule_texts = [r["rule_text"] for r in rules]
    repo_url = f"https://github.com/{full_name}.git"

    # Resolve installation_id: DB cache first, then GitHub API as fallback
    installation_id: int | None = None
    inst_row = db.get_installation_for_owner(str(user["id"]), owner)
    if inst_row:
        installation_id = inst_row["installation_id"]
    else:
        github_app = request.app.state.container.github_app
        installation_id = github_app.get_installation_id_for_repo(owner, repo)
        if installation_id:
            db.upsert_installation(installation_id, str(user["id"]), owner)

    task = db.create_task(
        repository_url=repo_url,
        repository_full_name=full_name,
        rules=rule_texts,
        user_id=str(user["id"]),
        enable_cross_check=cross_check,
        github_installation_id=installation_id,
    )
    return TaskCreatedResponse(task_id=str(task["id"]))


# Authenticated: list own tasks

@router.get(
    "/api/tasks",
    summary="List current user's tasks",
    response_model=list[TaskSummaryResponse],
)
async def list_tasks(
    request: Request,
    user: dict = Depends(get_current_user),
):
    db = request.app.state.database
    rows = db.get_user_tasks(str(user["id"]))
    return [
        TaskSummaryResponse(
            id=str(t["id"]),
            repository_full_name=t["repository_full_name"],
            status=t["status"],
            progress=t.get("progress", 0),
            progress_message=t.get("progress_message", ""),
            created_at=str(t["created_at"]),
        )
        for t in rows
    ]


@router.get(
    "/api/tasks/{task_id}",
    summary="Get task status and result",
    response_model=TaskDetailResponse,
)
async def get_task(
    task_id: str,
    request: Request,
    user: dict = Depends(get_current_user),
):
    db = request.app.state.database
    task = db.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if not db.can_view_task(task_id, str(user["id"])):
        raise HTTPException(status_code=403, detail="Access forbidden")

    result = _parse_task_result(task.get("result"))
    rules = task["rules"]
    if isinstance(rules, str):
        rules = json.loads(rules)

    return TaskDetailResponse(
        id=str(task["id"]),
        repository_url=task["repository_url"],
        repository_full_name=task["repository_full_name"],
        rules=rules,
        status=task["status"],
        progress=task.get("progress", 0),
        progress_message=task.get("progress_message", ""),
        result=result,
        error=task.get("error"),
        created_at=str(task["created_at"]),
        started_at=str(task["started_at"]) if task.get("started_at") else None,
        completed_at=(
            str(task["completed_at"]) if task.get("completed_at") else None
        ),
    )


# WebSocket: real-time task updates for authenticated users

@router.websocket("/ws/tasks")
async def ws_tasks(websocket: WebSocket):
    """Authenticate via first message `{"token": "xxx"}` and push
    task progress / completion events to the connected client.
    """
    await websocket.accept()

    try:
        auth_text = await websocket.receive_text()
        auth_data = json.loads(auth_text)
        token = auth_data.get("token", "")
    except Exception:
        await websocket.close(code=4001, reason="Invalid auth message")
        return

    if not token:
        await websocket.close(code=4001, reason="Missing token")
        return

    db = websocket.app.state.database
    user = db.get_user_by_token(token)
    if not user:
        await websocket.close(code=4001, reason="Invalid token")
        return

    ws_manager = websocket.app.state.ws_manager
    user_id = str(user["id"])
    await ws_manager.connect(websocket, user_id)

    try:
        # Keep alive -- client sends periodic pings, server pushes events
        while True:
            await websocket.receive_text()
    except Exception:
        ws_manager.disconnect(websocket, user_id)


# Helpers

def _parse_task_result(raw) -> TaskResultResponse | None:
    """Parse the JSONB result column into the response schema."""
    if not raw:
        return None
    data = raw if isinstance(raw, dict) else json.loads(raw)
    return TaskResultResponse(
        repomap=data.get("repomap", ""),
        summary=data.get("summary", ""),
        validations=[
            RuleValidationResponse(
                rule=v["rule"],
                related_files=[
                    FileMatchResponse(**f)
                    for f in v.get("related_files", [])
                ],
                match_count=len(v.get("related_files", [])),
                evaluation=(
                    RuleEvaluationResponse(**v["evaluation"])
                    if v.get("evaluation")
                    else None
                ),
                cross_check=(
                    CrossCheckResponse(**v["cross_check"])
                    if v.get("cross_check")
                    else None
                ),
            )
            for v in data.get("validations", [])
        ],
        embedding_model=data.get("embedding_model", ""),
        chunking_strategy=data.get("chunking_strategy", ""),
        llm_model=data.get("llm_model", ""),
    )
