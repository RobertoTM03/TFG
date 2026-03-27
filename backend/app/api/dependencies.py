from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

security = HTTPBearer()


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Validate the Bearer token and return the user row."""
    user = request.app.state.database.get_user_by_token(credentials.credentials)
    if not user:
        raise HTTPException(
            status_code=401, detail="Invalid or expired token",
        )
    return user
