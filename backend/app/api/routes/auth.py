import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse

from app.api.dependencies import get_current_user
from app.api.schemas import UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])

_GITHUB_AUTH_URL = "https://github.com/login/oauth/authorize"
_GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
_GITHUB_USER_URL = "https://api.github.com/user"


@router.get(
    "/login",
    summary="Redirect to GitHub OAuth",
    response_class=RedirectResponse,
)
async def login(request: Request):
    """Redirect the user's browser to the GitHub OAuth authorisation page."""
    settings = request.app.state.settings
    params = (
        f"client_id={settings.GITHUB_CLIENT_ID}"
        f"&scope=read:user user:email"
        f"&redirect_uri={settings.GITHUB_CALLBACK_URL}"
    )
    return RedirectResponse(f"{_GITHUB_AUTH_URL}?{params}")


@router.get(
    "/callback",
    summary="Handle GitHub OAuth callback",
    response_class=RedirectResponse,
)
async def callback(code: str, request: Request):
    """Exchange the temporary code for a long-lived access token, upsert
    the user record, and redirect the browser to the frontend with the
    token as a query parameter."""
    settings = request.app.state.settings
    db = request.app.state.database

    # Exchange code for access token
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            _GITHUB_TOKEN_URL,
            data={
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "code": code,
            },
            headers={"Accept": "application/json"},
        )
        token_data = resp.json()

    access_token = token_data.get("access_token")
    if not access_token:
        return RedirectResponse(
            f"{settings.FRONTEND_URL}?error=auth_failed",
        )

    # Fetch GitHub user profile
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            _GITHUB_USER_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            },
        )
        gh_user = resp.json()

    # Persist user
    db.upsert_user(
        github_id=gh_user["id"],
        github_login=gh_user["login"],
        avatar_url=gh_user.get("avatar_url", ""),
        access_token=access_token,
    )

    return RedirectResponse(f"{settings.FRONTEND_URL}?token={access_token}")


@router.get("/me", summary="Current user info", response_model=UserResponse)
async def me(user: dict = Depends(get_current_user)):
    """Return profile data for the authenticated user."""
    return UserResponse(
        id=str(user["id"]),
        github_id=user["github_id"],
        github_login=user["github_login"],
        avatar_url=user["avatar_url"],
    )
