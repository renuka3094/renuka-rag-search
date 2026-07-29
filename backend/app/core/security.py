"""
API-key auth (Section 6.2: "at least API-key authentication").

This is intentionally simple: one shared secret in an env var, sent as the
X-API-Key header. It is enough to satisfy "not a wide-open endpoint" for an
internal pilot. If this graduates past a pilot, swap this dependency for
Azure AD / Entra ID auth (OAuth2 bearer tokens) without touching any route
handlers, since they only depend on `require_api_key`.
"""
from fastapi import Header, HTTPException, status

from app.core.config import get_settings


async def require_api_key(x_api_key: str = Header(default="")) -> None:
    settings = get_settings()
    if not x_api_key or x_api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API key. Send it as the 'X-API-Key' header.",
        )
