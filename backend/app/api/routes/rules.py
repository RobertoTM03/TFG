from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.api.dependencies import get_current_user
from app.infrastructure.limiter import limiter, rate_limit_default
from app.api.schemas import (
    CreateRuleRequest,
    PaginatedResponse,
    RuleResponse,
)

router = APIRouter(prefix="/api", tags=["Rules"])


@router.get(
    "/repos/{owner}/{repo}/rules",
    summary="List rules for a repository",
    response_model=PaginatedResponse[RuleResponse],
)
@limiter.limit(rate_limit_default)
async def list_rules(
    owner: str,
    repo: str,
    request: Request,
    user: dict = Depends(get_current_user),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    sort_by: str = Query("position", description="Sort column: position | rule_text"),
    sort_order: str = Query("asc", pattern="^(asc|desc)$", description="asc or desc"),
):
    db = request.app.state.database
    full_name = f"{owner}/{repo}"
    rows, total = db.get_rules(
        str(user["id"]), full_name,
        page=page, page_size=page_size,
        sort_by=sort_by, sort_order=sort_order,
    )
    total_pages = max(1, -(-total // page_size))  # ceiling division
    return PaginatedResponse[RuleResponse](
        items=[
            RuleResponse(
                id=str(r["id"]),
                rule_text=r["rule_text"],
                position=r["position"],
            )
            for r in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post(
    "/repos/{owner}/{repo}/rules",
    status_code=201,
    summary="Create a new rule",
    response_model=RuleResponse,
)
@limiter.limit(rate_limit_default)
async def create_rule(
    owner: str,
    repo: str,
    body: CreateRuleRequest,
    request: Request,
    user: dict = Depends(get_current_user),
):
    db = request.app.state.database
    full_name = f"{owner}/{repo}"

    settings = request.app.state.settings
    count = db.count_rules(str(user["id"]), full_name)
    if count >= settings.MAX_RULES_PER_REPO:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum of {settings.MAX_RULES_PER_REPO} rules per repository reached",
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
@limiter.limit(rate_limit_default)
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
