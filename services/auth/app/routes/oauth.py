import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.repositories.user_repository import UserRepository

# from app.schemas.auth_schema import OAuthCodeRequest, TokenResponse
from app.services.jwt_service import create_access_token
from app.services.oauth_service import (
    OAuthError,
    # exchange_github_code,
    exchange_google_code,
)
from app.utils.oauth_config import get_oauth_settings

router = APIRouter()


@router.get("/auth/oauth/google/callback")
def google_callback(code: str, db: Session = Depends(get_db)):
    try:
        settings = get_oauth_settings()
    except RuntimeError:
        raise HTTPException(status_code=503, detail="Login method disabled")
    if not settings.google_enabled:
        raise HTTPException(status_code=503, detail="Login method disabled")

    redirect_uri = settings.google_redirect_uri

    try:
        user_info = exchange_google_code(
            settings.google_client_id,
            settings.google_client_secret,
            code,
            redirect_uri,
        )
    except OAuthError:
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost")
        return RedirectResponse(url=f"{frontend_url}/index.html?error=oauth_failed")

    if not user_info.get("email") or not user_info.get("oauth_id"):
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost")
        return RedirectResponse(url=f"{frontend_url}/index.html?error=oauth_failed")

    repo = UserRepository(db)
    user, _ = repo.upsert_oauth_user(
        email=user_info["email"],
        provider="google",
        oauth_id=user_info["oauth_id"],
        full_name=user_info.get("full_name"),
        institution_id=1,
    )
    if not user.is_active:
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost")
        return RedirectResponse(url=f"{frontend_url}/index.html?error=inactive")

    token = create_access_token(
        {
            "sub": user.id,
            "email": user.email,
            "role": user.role,
            "institution_id": user.institution_id,
        }
    )

    frontend_url = os.getenv("FRONTEND_URL", "http://localhost")
    return RedirectResponse(url=f"{frontend_url}/oauth-success.html#token={token}")
