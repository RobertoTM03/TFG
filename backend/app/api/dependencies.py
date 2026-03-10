from fastapi import Header, HTTPException, Request

from app.infrastructure.database import Database


async def get_db(request: Request) -> Database:
    """Retrieve the Database instance from application state."""
    return request.app.state.database


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
    db: Database = request.app.state.database
    user = db.get_user_by_token(token)
    if not user:
        raise HTTPException(
            status_code=401, detail="Invalid or expired token",
        )
    return user
