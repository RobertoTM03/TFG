from fastapi import APIRouter, Depends, Request

from app.api.dependencies import extract_bearer_token, get_current_user
from app.infrastructure.limiter import limiter, rate_limit_default

router = APIRouter(prefix="/api", tags=["Repositories"])


@router.get("/app-info", summary="GitHub App public metadata")
async def app_info(request: Request):
    """Returns public GitHub App info and available LLM models."""
    return request.app.state.container.get_app_info()


@router.get("/repos", summary="List repositories where the GitHub App is installed")
@limiter.limit(rate_limit_default)
async def list_repos(
    request: Request,
    user: dict = Depends(get_current_user),
):
    """Return all repos accessible through the user's GitHub App installations."""
    github_app = request.app.state.container.github_app
    user_token = extract_bearer_token(request)

    repo_config_repo = request.app.state.repo_config_repo
    installations = github_app.get_user_installations(user_token)
    repos = []
    for inst in installations:
        inst_repos = github_app.get_installation_repos(user_token, inst.installation_id)
        for r in inst_repos:
            config = repo_config_repo.get_repo_config(str(user["id"]), r.full_name)
            pr_evaluation_enabled = config["pr_evaluation_enabled"] if config else True
            repos.append({
                "installation_id": r.installation_id,
                "full_name": r.full_name,
                "name": r.name,
                "private": r.private,
                "description": r.description,
                "language": r.language,
                "stargazers_count": r.stargazers_count,
                "clone_url": r.clone_url,
                "html_url": r.html_url,
                "pr_evaluation_enabled": pr_evaluation_enabled,
            })

    return repos



@router.get("/installations", summary="List the user's GitHub App installations")
@limiter.limit(rate_limit_default)
async def list_installations(
    request: Request,
    user: dict = Depends(get_current_user),
):
    """Return all GitHub App installations the user can access."""
    github_app = request.app.state.container.github_app
    installations = github_app.get_user_installations(extract_bearer_token(request))
    return [
        {
            "installation_id": i.installation_id,
            "account_login": i.account_login,
            "account_type": i.account_type,
        }
        for i in installations
    ]
