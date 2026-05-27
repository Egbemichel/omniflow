import os
from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.repositories.user_repository import UserRepository
from app.services.jwt_service import create_access_token
from app.services.magic_link_service import MagicLinkService, get_magic_link_config
from app.services.email_service import send_magic_link
from pydantic import BaseModel, EmailStr

router = APIRouter()


class MagicLinkRequest(BaseModel):
    email: EmailStr


# ── Dependency — tests can override this via app.dependency_overrides ───────
def get_magic_link_service() -> MagicLinkService:
    return MagicLinkService(get_magic_link_config())


@router.post("/magic-link/request")
def request_magic_link(
    payload: MagicLinkRequest,
    svc: MagicLinkService = Depends(get_magic_link_service),
):
    token = svc.generate_token(payload.email)
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost")
    link = f"{frontend_url}/api/auth/magic-link/verify?token={token}"
    send_magic_link(payload.email, link)
    return {"message": "If that email is registered, a sign-in link has been sent."}


@router.get("/magic-link/verify")
def verify_magic_link(
    token: str,
    db: Session = Depends(get_db),
    svc: MagicLinkService = Depends(get_magic_link_service),
):
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost")

    try:
        email = svc.verify_token(token)
    except ValueError:
        return RedirectResponse(url=f"{frontend_url}/login.html?error=invalid_link")

    if not email:
        return RedirectResponse(url=f"{frontend_url}/login.html?error=invalid_link")

    repo = UserRepository(db)
    user = repo.get_by_email(email)
    if not user:
        user, _ = repo.upsert_oauth_user(
            email=email,
            provider="magic_link",
            oauth_id=email,
            full_name=None,
            institution_id=1,
        )

    if not user.is_active:
        return RedirectResponse(url=f"{frontend_url}/login.html?error=inactive")

    token_jwt = create_access_token(
        {
            "sub": user.id,
            "email": user.email,
            "role": user.role,
            "institution_id": user.institution_id,
        }
    )

    return RedirectResponse(url=f"{frontend_url}/oauth-success.html#token={token_jwt}")
