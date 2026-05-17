from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.repositories.user_repository import UserRepository
from app.routes.dependencies import require_admin
from app.schemas.user_schema import RoleAssign, UserResponse

router = APIRouter()


@router.get("/admin/users", response_model=list[UserResponse])
def list_users(db: Session = Depends(get_db), admin=Depends(require_admin)):
    repo = UserRepository(db)
    return repo.list_by_institution(admin.institution_id)


@router.put("/admin/users/{user_id}/role", response_model=UserResponse)
def assign_role(
    user_id: str,
    payload: RoleAssign,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    repo = UserRepository(db)
    user = repo.get_by_id(user_id)
    if not user or user.institution_id != admin.institution_id:
        raise HTTPException(status_code=404, detail="User not found")
    return repo.assign_role(user, payload.role)
