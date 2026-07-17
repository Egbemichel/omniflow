from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.repositories.user_repository import UserRepository
from app.services.jwt_service import decode_token


@dataclass
class HeaderUser:
    id: str
    role: str
    institution_id: int
    email: str = "mock@example.com"
    full_name: Optional[str] = None
    actor_type: Optional[str] = None
    is_active: bool = True


def get_current_user(
    authorization: Optional[str] = Header(None),
    # Internal/test authentication headers
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
    x_institution_id: Optional[str] = Header(None, alias="X-Institution-Id"),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    x_user_email: Optional[str] = Header(None, alias="X-User-Email"),
    x_user_name: Optional[str] = Header(None, alias="X-User-Name"),
    x_actor_type: Optional[str] = Header(None, alias="X-Actor-Type"),
    db: Session = Depends(get_db),
):
    """
    Authentication order:

    1. Real JWT Bearer Token
    2. Trusted X-User-* headers (used by tests/internal services)
    """

    # ---------------------------------------------------------
    # Normal JWT Authentication
    # ---------------------------------------------------------
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]

        payload = decode_token(token)

        if not payload:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired token",
            )

        repo = UserRepository(db)
        user = repo.get_by_id(payload.get("sub"))

        if not user:
            raise HTTPException(
                status_code=401,
                detail="User not found",
            )

        if not getattr(user, "is_active", True):
            raise HTTPException(
                status_code=401,
                detail="User inactive",
            )

        return user

    # ---------------------------------------------------------
    # Trusted Header Authentication
    # (Used by unit tests and internal service calls)
    # ---------------------------------------------------------
    if x_user_role:
        try:
            institution_id = int(x_institution_id) if x_institution_id else 1

        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid institution header",
            )

        return HeaderUser(
            id=x_user_id or "mock-user-id",
            role=x_user_role,
            institution_id=institution_id,
            email=x_user_email or "mock@example.com",
            full_name=x_user_name,
            actor_type=x_actor_type,
            is_active=True,
        )

    # ---------------------------------------------------------
    # No Authentication
    # ---------------------------------------------------------
    raise HTTPException(
        status_code=401,
        detail="Not authenticated",
    )


def require_admin(current_user=Depends(get_current_user)):
    """
    Allows:
        - admin
        - institution_admin
        - super_admin
    """

    if current_user.role not in (
        "admin",
        "institution_admin",
        "super_admin",
    ):
        raise HTTPException(
            status_code=403,
            detail="Admin access required",
        )

    return current_user


def require_super_admin(current_user=Depends(get_current_user)):
    """
    Allows only super admins.
    """

    if current_user.role != "super_admin":
        raise HTTPException(
            status_code=403,
            detail="Super Admin access required",
        )

    return current_user


def require_institution_admin(current_user=Depends(get_current_user)):
    """
    Allows:
        - institution_admin
        - super_admin
    """

    if current_user.role not in (
        "institution_admin",
        "super_admin",
    ):
        raise HTTPException(
            status_code=403,
            detail="Institution Admin access required",
        )

    return current_user
