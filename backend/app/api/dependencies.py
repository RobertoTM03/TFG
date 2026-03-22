from fastapi import Header, HTTPException, Request


async def get_current_user(
    request: Request,
    authorization: str = Header(
        ..., description="Bearer <github_access_token>",
    ),
) -> dict:
    """Validate the Bearer token and return the user row."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401, detail="Missing or invalid Authorization header",
        )
    token = authorization[7:]
    user = request.app.state.database.get_user_by_token(token)
    if not user:
        raise HTTPException(
            status_code=401, detail="Invalid or expired token",
        )
    return user
