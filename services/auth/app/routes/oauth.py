import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.repositories.user_repository import UserRepository

from app.schemas.auth_schema import OAuthCodeRequest, TokenResponse
from app.services.jwt_service import create_access_token
from app.services.oauth_service import (
    OAuthError,
    exchange_github_code,
    exchange_google_code,
)
from app.utils.oauth_config import get_oauth_settings

router = APIRouter()


def _token_response_for_oauth_user(
    db: Session,
    *,
    provider: str,
    user_info: dict,
) -> dict:
    if not user_info.get("email") or not user_info.get("oauth_id"):
        raise HTTPException(status_code=401, detail="Login failed")

    repo = UserRepository(db)
    user, _ = repo.upsert_oauth_user(
        email=user_info["email"],
        provider=provider,
        oauth_id=user_info["oauth_id"],
        full_name=user_info.get("full_name"),
        institution_id=1,
    )
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User inactive")

    token = create_access_token(
        {
            "sub": user.id,
            "email": user.email,
            "role": user.role,
            "institution_id": user.institution_id,
        }
    )
    return {"access_token": token, "token_type": "bearer"}


@router.post("/google", response_model=TokenResponse)
def google_login(payload: OAuthCodeRequest, db: Session = Depends(get_db)):
    try:
        settings = get_oauth_settings()
    except RuntimeError:
        raise HTTPException(status_code=503, detail="Login method disabled")
    if not settings.google_enabled:
        raise HTTPException(status_code=503, detail="Login method disabled")

    try:
        user_info = exchange_google_code(
            settings.google_client_id,
            settings.google_client_secret,
            payload.code,
            payload.redirect_uri,
        )
    except OAuthError:
        raise HTTPException(status_code=401, detail="Login failed")

    return _token_response_for_oauth_user(db, provider="google", user_info=user_info)


@router.post("/github", response_model=TokenResponse)
def github_login(payload: OAuthCodeRequest, db: Session = Depends(get_db)):
    try:
        settings = get_oauth_settings()
    except RuntimeError:
        raise HTTPException(status_code=503, detail="Login method disabled")
    if not settings.github_enabled:
        raise HTTPException(status_code=503, detail="Login method disabled")

    try:
        user_info = exchange_github_code(
            settings.github_client_id,
            settings.github_client_secret,
            payload.code,
            payload.redirect_uri,
        )
    except OAuthError:
        raise HTTPException(status_code=401, detail="Login failed")

    return _token_response_for_oauth_user(db, provider="github", user_info=user_info)


@router.get("/oauth/google/callback")
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

    try:
        token_response = _token_response_for_oauth_user(
            db, provider="google", user_info=user_info
        )
    except HTTPException:
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost")
        return RedirectResponse(url=f"{frontend_url}/index.html?error=oauth_failed")

    frontend_url = os.getenv("FRONTEND_URL", "http://localhost")
    return RedirectResponse(
        url=f"{frontend_url}/oauth-success.html#token={token_response['access_token']}"
    )


@router.get("/oauth/github/callback")
def github_callback(code: str, db: Session = Depends(get_db)):
    try:
        settings = get_oauth_settings()
    except RuntimeError:
        raise HTTPException(status_code=503, detail="Login method disabled")
    if not settings.github_enabled:
        raise HTTPException(status_code=503, detail="Login method disabled")

    redirect_uri = os.getenv(
        "GITHUB_REDIRECT_URI", "http://localhost/auth/oauth/github/callback"
    )

    try:
        user_info = exchange_github_code(
            settings.github_client_id,
            settings.github_client_secret,
            code,
            redirect_uri,
        )
    except OAuthError:
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost")
        return RedirectResponse(url=f"{frontend_url}/login.html?error=oauth_failed")

    try:
        token_response = _token_response_for_oauth_user(
            db, provider="github", user_info=user_info
        )
    except HTTPException:
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost")
        return RedirectResponse(url=f"{frontend_url}/login.html?error=oauth_failed")

    frontend_url = os.getenv("FRONTEND_URL", "http://localhost")
    return RedirectResponse(
        url=f"{frontend_url}/oauth-success.html#token={token_response['access_token']}"
    )
