from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import Optional, List

from app import schemas, services
from app.database import get_db

router = APIRouter()


# ── Dependency: extract and validate Bearer token ────────────────────────────


def _get_token(authorization: Optional[str] = Header(None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return authorization.split(" ", 1)[1]


def _get_current_user(token: str = Depends(_get_token), db: Session = Depends(get_db)):
    payload = services.decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = services.get_user_by_id(db, payload.get("sub"))
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user


def _require_admin(current_user=Depends(_get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


# ── Auth routes ──────────────────────────────────────────────────────────────


@router.post("/auth/register", response_model=schemas.UserResponse, status_code=201)
def register(payload: schemas.UserRegister, db: Session = Depends(get_db)):
    if services.get_user_by_email(db, payload.email):
        raise HTTPException(status_code=409, detail="Email already registered")
    return services.register_user(db, payload)


@router.post("/auth/login", response_model=schemas.TokenResponse)
def login(payload: schemas.UserLogin, db: Session = Depends(get_db)):
    user = services.authenticate_user(db, payload)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = services.create_access_token(
        {"sub": user.id, "email": user.email, "role": user.role}
    )
    return {"access_token": token, "token_type": "bearer"}


@router.get("/auth/verify", response_model=schemas.TokenVerifyResponse)
def verify_token(current_user=Depends(_get_current_user)):
    return {
        "user_id": current_user.id,
        "email": current_user.email,
        "role": current_user.role,
    }


# ── Admin routes ─────────────────────────────────────────────────────────────


@router.get("/admin/users", response_model=List[schemas.UserResponse])
def list_users(db: Session = Depends(get_db), _=Depends(_require_admin)):
    return services.list_users(db)


@router.put("/admin/users/{user_id}/role", response_model=schemas.UserResponse)
def assign_role(
    user_id: str,
    payload: schemas.RoleAssign,
    db: Session = Depends(get_db),
    _=Depends(_require_admin),
):
    user = services.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return services.assign_role(db, user, payload.role)
