from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.repositories.user_repository import UserRepository
from app.schemas.auth_schema import MagicLinkRequest, MagicLinkVerify, TokenResponse
from app.services.jwt_service import create_access_token
from app.services.magic_link_service import MagicLinkService, get_magic_link_config
from app.utils.oauth_config import get_oauth_settings

router = APIRouter()


def get_magic_link_service() -> MagicLinkService:
    settings = get_oauth_settings()
    if not settings.magic_link_enabled:
        raise HTTPException(status_code=503, detail="Login method disabled")
    config = get_magic_link_config()
    return MagicLinkService(config)


@router.post("/auth/magic-link/request")
def request_magic_link(
    payload: MagicLinkRequest,
    service: MagicLinkService = Depends(get_magic_link_service),
):
    try:
        token = service.generate_token(payload.email)
    except Exception:
        raise HTTPException(status_code=500, detail="Login failed")
    return {"message": "Magic link sent", "token": token}


@router.post("/auth/magic-link/verify", response_model=TokenResponse)
def verify_magic_link(
    payload: MagicLinkVerify,
    db: Session = Depends(get_db),
    service: MagicLinkService = Depends(get_magic_link_service),
):
    try:
        email = service.verify_token(payload.token)
    except Exception:
        raise HTTPException(status_code=401, detail="Login failed")

    if not email:
        raise HTTPException(status_code=401, detail="Login failed")

    repo = UserRepository(db)
    user, _ = repo.upsert_oauth_user(
        email=email,
        provider="magic_link",
        oauth_id=email,
        full_name=None,
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
