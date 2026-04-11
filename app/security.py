from fastapi import Header, HTTPException

from app.config import settings


def _extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


def require_admin(
    authorization: str | None = Header(default=None),
    x_admin_token: str | None = Header(default=None),
) -> None:
    if not settings.admin_auth_enabled:
        return

    bearer_value = authorization if isinstance(authorization, str) else None
    header_value = x_admin_token if isinstance(x_admin_token, str) else None
    token = header_value or _extract_bearer_token(bearer_value)
    if token == settings.admin_api_token:
        return

    raise HTTPException(status_code=401, detail="unauthorized")
