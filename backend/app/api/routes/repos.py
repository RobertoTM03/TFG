import httpx
from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_user

router = APIRouter(prefix="/api", tags=["Repositories"])


@router.get("/repos", summary="List user repositories from GitHub")
async def list_repos(user: dict = Depends(get_current_user)):
    """Return the authenticated user's GitHub repositories sorted by
    most recently updated."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.github.com/user/repos",
            headers={
                "Authorization": f"Bearer {user['access_token']}",
                "Accept": "application/vnd.github.v3+json",
            },
            params={
                "per_page": 100,
                "sort": "updated",
                "type": "all",
            },
        )
        resp.raise_for_status()
        repos = resp.json()

    return [
        {
            "full_name": r["full_name"],
            "name": r["name"],
            "description": r.get("description"),
            "language": r.get("language"),
            "private": r["private"],
            "stargazers_count": r.get("stargazers_count", 0),
            "updated_at": r.get("updated_at"),
            "clone_url": r["clone_url"],
            "html_url": r["html_url"],
        }
        for r in repos
    ]
