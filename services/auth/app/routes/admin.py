from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.repositories.user_repository import UserRepository
from app.routes.dependencies import require_admin
from app.schemas.user_schema import RoleAssign, UserResponse, UserUpdate

router = APIRouter()


@router.get("/admin/users", response_model=list[UserResponse])
def list_users(db: Session = Depends(get_db), admin=Depends(require_admin)):
    repo = UserRepository(db)
    if admin.role == "super_admin":
        return repo.list_all()
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
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if admin.role != "super_admin" and user.institution_id != admin.institution_id:
        raise HTTPException(status_code=404, detail="User not found")

    return repo.assign_role(user, payload.role)


@router.put("/admin/users/{user_id}", response_model=UserResponse)
def update_user(
    user_id: str,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    repo = UserRepository(db)
    user = repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if admin.role != "super_admin" and user.institution_id != admin.institution_id:
        raise HTTPException(status_code=404, detail="User not found")
    if payload.role == "super_admin" and admin.role != "super_admin":
        raise HTTPException(
            status_code=403, detail="Only super_admin can assign super_admin"
        )

    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.role is not None:
        user.role = payload.role
    if "actor_type" in payload.model_fields_set:
        user.actor_type = payload.actor_type
    if payload.is_active is not None:
        user.is_active = payload.is_active

    db.commit()
    db.refresh(user)
    return user


@router.delete("/admin/users/{user_id}")
def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    repo = UserRepository(db)
    user = repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if admin.role != "super_admin" and user.institution_id != admin.institution_id:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == admin.id:
        raise HTTPException(
            status_code=400, detail="You cannot delete your own account"
        )
    if user.role == "super_admin" and admin.role != "super_admin":
        raise HTTPException(
            status_code=403, detail="Only super_admin can delete super_admin"
        )

    db.delete(user)
    db.commit()
    return {"status": "deleted", "user_id": user_id}
