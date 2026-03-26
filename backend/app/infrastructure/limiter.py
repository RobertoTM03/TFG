from fastapi import Request
from slowapi import Limiter

from app.config import Settings


def _get_user_token(request: Request) -> str:
    """Use the bearer token as the rate-limit key (per authenticated user)."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return request.client.host  # fallback for unauthenticated requests


limiter = Limiter(key_func=_get_user_token)

# Mutable reference populated at startup from Settings (avoids os.getenv bypass)
_settings: list[Settings | None] = [None]


def init_limiter(settings: Settings) -> None:
    """Called once at app startup to wire Settings into the limiter."""
    _settings[0] = settings


def rate_limit_validate() -> str:
    s = _settings[0]
    return s.RATE_LIMIT_VALIDATE if s else "10/minute"


def rate_limit_default() -> str:
    s = _settings[0]
    return s.RATE_LIMIT_DEFAULT if s else "100/minute"
