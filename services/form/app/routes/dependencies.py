from fastapi import Depends, Header, HTTPException
from typing import Optional
from app.services.auth_client import AuthClient, AuthClientError


def get_token(authorization: Optional[str] = Header(None)) -> str:  # pragma: no cover
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return authorization.split(" ", 1)[1]


def get_auth_client() -> AuthClient:  # pragma: no cover
    return AuthClient()


def get_current_user(  # pragma: no cover
    token: str = Depends(get_token), auth_client: AuthClient = Depends(get_auth_client)
) -> dict:
    try:
        payload = auth_client.verify_token(token)
    except AuthClientError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    if "institution_id" not in payload:
        raise HTTPException(status_code=502, detail="Auth service error")

    return payload


def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user
