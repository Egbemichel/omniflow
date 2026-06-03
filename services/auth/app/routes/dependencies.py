from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.repositories.user_repository import UserRepository
from app.services.jwt_service import decode_token


def get_token(authorization: Optional[str] = Header(None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return authorization.split(" ", 1)[1]


def get_current_user(token: str = Depends(get_token), db: Session = Depends(get_db)):
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    repo = UserRepository(db)
    user = repo.get_by_id(payload.get("sub"))
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user


def require_admin(current_user=Depends(get_current_user)):
    if current_user.role not in ["super_admin", "institution_admin", "admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


def require_super_admin(current_user=Depends(get_current_user)):
    if current_user.role != "super_admin":
        raise HTTPException(status_code=403, detail="Super Admin access required")
    return current_user


def require_institution_admin(current_user=Depends(get_current_user)):
    if current_user.role not in ["super_admin", "institution_admin"]:
        raise HTTPException(status_code=403, detail="Institution Admin access required")
    return current_user
