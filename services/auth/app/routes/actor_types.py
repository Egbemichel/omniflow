import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.actor_type import ActorType
from app.routes.dependencies import require_admin
from app.schemas.actor_type_schema import ActorTypeCreate, ActorTypeResponse

router = APIRouter()


@router.get("/admin/actor-types", response_model=list[ActorTypeResponse])
def list_actor_types(db: Session = Depends(get_db), admin=Depends(require_admin)):
    return (
        db.query(ActorType)
        .filter(ActorType.institution_id == admin.institution_id)
        .order_by(ActorType.label.asc())
        .all()
    )


@router.post("/admin/actor-types", response_model=ActorTypeResponse, status_code=201)
def create_actor_type(
    payload: ActorTypeCreate,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    label = payload.label.strip()
    exists = (
        db.query(ActorType)
        .filter(
            ActorType.institution_id == admin.institution_id,
            ActorType.label == label,
        )
        .first()
    )
    if exists:
        raise HTTPException(status_code=409, detail="Actor type already exists")

    actor_type = ActorType(
        id=str(uuid.uuid4()),
        institution_id=admin.institution_id,
        label=label,
        system_role=payload.system_role.value,
    )
    db.add(actor_type)
    db.commit()
    db.refresh(actor_type)
    return actor_type


@router.delete("/admin/actor-types/{actor_type_id}", status_code=204)
def delete_actor_type(
    actor_type_id: str,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    actor_type = (
        db.query(ActorType)
        .filter(
            ActorType.id == actor_type_id,
            ActorType.institution_id == admin.institution_id,
        )
        .first()
    )
    if not actor_type:
        raise HTTPException(status_code=404, detail="Actor type not found")
    db.delete(actor_type)
    db.commit()
    return None
