from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.repositories.user_repository import UserRepository
from app.schemas.auth_schema import MagicLinkRequest, TokenResponse
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


@router.post("/auth/magic/login")
def request_magic_link(
    payload: MagicLinkRequest,
    service: MagicLinkService = Depends(get_magic_link_service),
):
    try:
        token = service.generate_token(payload.email)
        # In DEV, we can see the link in logs
        print(
            f"DEBUG: Magic Link for {payload.email}: http://localhost/login.html?token={token}"
        )
    except Exception:
        raise HTTPException(status_code=500, detail="Login failed")
    return {"msg": "Magic link sent", "token": token}


@router.get("/auth/magic/verify", response_model=TokenResponse)
def verify_magic_link(
    token: str,
    db: Session = Depends(get_db),
    service: MagicLinkService = Depends(get_magic_link_service),
):
    try:
        email = service.verify_token(token)
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
