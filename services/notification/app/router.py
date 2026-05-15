from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import Optional, List

from app import schemas, services
from app.database import get_db

router = APIRouter()


@router.post("/notifications", response_model=schemas.NotificationOut, status_code=201)
def create_notification(
    payload: schemas.NotificationCreate,
    db: Session = Depends(get_db),
    x_user_role: Optional[str] = Header(None),
):
    # Only internal services (acting as admin) or admins can push notifications
    if x_user_role not in ("admin",):
        raise HTTPException(status_code=403, detail="Forbidden")
    return services.create_notification(
        db, payload.recipient_id, payload.event_type, payload.message
    )


@router.get("/notifications", response_model=List[schemas.NotificationOut])
def get_my_notifications(
    db: Session = Depends(get_db),
    x_user_id: Optional[str] = Header(None),
    x_user_role: Optional[str] = Header(None),
):
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    return services.get_notifications(db, x_user_id)


@router.patch(
    "/notifications/{notification_id}/read", response_model=schemas.NotificationOut
)
def mark_read(
    notification_id: str,
    db: Session = Depends(get_db),
    x_user_id: Optional[str] = Header(None),
):
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    n = services.mark_read(db, notification_id)
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found")
    return n
