from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

security = HTTPBearer()


def extract_bearer_token(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    return auth[7:]


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Validate the Bearer token and return the user row."""
    user = request.app.state.user_repo.get_user_by_token(credentials.credentials)
    if not user:
        raise HTTPException(
            status_code=401, detail="Invalid or expired token",
        )
    return user
