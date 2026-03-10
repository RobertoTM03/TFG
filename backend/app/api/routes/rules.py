from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.dependencies import get_current_user
from app.api.schemas import CreateRuleRequest, RuleResponse, RulesListResponse

router = APIRouter(prefix="/api", tags=["Rules"])


@router.get(
    "/repos/{owner}/{repo}/rules",
    summary="List rules for a repository",
    response_model=RulesListResponse,
)
async def list_rules(
    owner: str,
    repo: str,
    request: Request,
    user: dict = Depends(get_current_user),
):
    db = request.app.state.database
    full_name = f"{owner}/{repo}"
    rows = db.get_rules(str(user["id"]), full_name)
    return RulesListResponse(
        rules=[
            RuleResponse(
                id=str(r["id"]),
                rule_text=r["rule_text"],
                position=r["position"],
            )
            for r in rows
        ],
        count=len(rows),
    )


@router.post(
    "/repos/{owner}/{repo}/rules",
    status_code=201,
    summary="Create a new rule",
    response_model=RuleResponse,
)
async def create_rule(
    owner: str,
    repo: str,
    body: CreateRuleRequest,
    request: Request,
    user: dict = Depends(get_current_user),
):
    db = request.app.state.database
    full_name = f"{owner}/{repo}"

    count = db.count_rules(str(user["id"]), full_name)
    if count >= 10:
        raise HTTPException(
            status_code=400,
            detail="Maximum of 10 rules per repository reached",
        )

    rule = db.create_rule(str(user["id"]), full_name, body.rule_text)
    return RuleResponse(
        id=str(rule["id"]),
        rule_text=rule["rule_text"],
        position=rule["position"],
    )


@router.delete(
    "/repos/{owner}/{repo}/rules/{rule_id}",
    status_code=204,
    summary="Delete a rule",
)
async def delete_rule(
    owner: str,
    repo: str,
    rule_id: str,
    request: Request,
    user: dict = Depends(get_current_user),
):
    db = request.app.state.database
    deleted = db.delete_rule(rule_id, str(user["id"]))
    if not deleted:
        raise HTTPException(status_code=404, detail="Rule not found")
