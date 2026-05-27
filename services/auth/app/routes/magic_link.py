import os
from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.repositories.user_repository import UserRepository
from app.services.jwt_service import create_access_token
from app.services.magic_link_service import (
    build_magic_link,
    generate_magic_token,
    verify_magic_token,
)
from app.services.email_service import send_magic_link
from pydantic import BaseModel, EmailStr

router = APIRouter()


class MagicLinkRequest(BaseModel):
    email: EmailStr


@router.post("/magic-link/request")
def request_magic_link(payload: MagicLinkRequest):
    """Generate a token and email the magic link."""
    token = generate_magic_token(payload.email)
    link = build_magic_link(token)
    send_magic_link(payload.email, link)
    # Always return 200 even if email not registered (security best practice)
    return {"message": "If that email is registered, a sign-in link has been sent."}


@router.get("/magic-link/verify")
def verify_magic_link(token: str, db: Session = Depends(get_db)):
    """Verify the token, issue JWT, redirect to frontend."""
    email = verify_magic_token(token)
    if not email:
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost")
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
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost")
        return RedirectResponse(url=f"{frontend_url}/login.html?error=inactive")

    token_jwt = create_access_token(
        {
            "sub": user.id,
            "email": user.email,
            "role": user.role,
            "institution_id": user.institution_id,
        }
    )

    frontend_url = os.getenv("FRONTEND_URL", "http://localhost")
    return RedirectResponse(url=f"{frontend_url}/oauth-success.html#token={token_jwt}")
