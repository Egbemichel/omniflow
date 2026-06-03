from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.institution import Institution
from app.schemas.institution import (
    InstitutionCreate,
    InstitutionResponse,
    InstitutionUpdate,
)
from app.routes.dependencies import get_current_user

router = APIRouter(prefix="/institutions", tags=["Institutions"])


@router.post("/", response_model=InstitutionResponse)
def create_institution(
    institution: InstitutionCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if current_user.role != "super_admin":
        raise HTTPException(
            status_code=403, detail="Only super_admin can create institutions"
        )

    db_institution = Institution(name=institution.name, type=institution.type)
    db.add(db_institution)
    db.commit()
    db.refresh(db_institution)
    return db_institution


@router.get("/", response_model=List[InstitutionResponse])
def list_institutions(
    db: Session = Depends(get_db), current_user=Depends(get_current_user)
):
    if current_user.role != "super_admin":
        # Non-super admins only see their own institution
        return (
            db.query(Institution)
            .filter(Institution.id == current_user.institution_id)
            .all()
        )
    return db.query(Institution).all()


@router.get("/{institution_id}", response_model=InstitutionResponse)
def get_institution(
    institution_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if (
        current_user.role != "super_admin"
        and current_user.institution_id != institution_id
    ):
        raise HTTPException(
            status_code=403, detail="Not authorized to view this institution"
        )

    db_institution = (
        db.query(Institution).filter(Institution.id == institution_id).first()
    )
    if not db_institution:
        raise HTTPException(status_code=404, detail="Institution not found")
    return db_institution


@router.put("/{institution_id}", response_model=InstitutionResponse)
def update_institution(
    institution_id: int,
    institution: InstitutionUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if current_user.role != "super_admin":
        raise HTTPException(
            status_code=403, detail="Only super_admin can update institutions"
        )

    db_institution = (
        db.query(Institution).filter(Institution.id == institution_id).first()
    )
    if not db_institution:
        raise HTTPException(status_code=404, detail="Institution not found")
    if institution.name is not None:
        db_institution.name = institution.name
    if institution.type is not None:
        db_institution.type = institution.type
    db.commit()
    db.refresh(db_institution)
    return db_institution


@router.delete("/{institution_id}")
def delete_institution(
    institution_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if current_user.role != "super_admin":
        raise HTTPException(
            status_code=403, detail="Only super_admin can delete institutions"
        )
    if current_user.institution_id == institution_id:
        raise HTTPException(
            status_code=400, detail="You cannot delete your own institution"
        )

    db_institution = (
        db.query(Institution).filter(Institution.id == institution_id).first()
    )
    if not db_institution:
        raise HTTPException(status_code=404, detail="Institution not found")
    db.delete(db_institution)
    db.commit()
    return {"status": "deleted", "institution_id": institution_id}
