from sqlalchemy.orm import Session
from typing import List, Optional
from app import models


def create_notification(db: Session, recipient_id: str, event_type: str, message: str) -> models.Notification:
    n = models.Notification(recipient_id=recipient_id, event_type=event_type, message=message)
    db.add(n)
    db.commit()
    db.refresh(n)
    return n


def get_notifications(db: Session, recipient_id: str) -> List[models.Notification]:
    return db.query(models.Notification).filter(models.Notification.recipient_id == recipient_id).all()


def mark_read(db: Session, notification_id: str) -> Optional[models.Notification]:
    n = db.query(models.Notification).filter(models.Notification.id == notification_id).first()
    if n:
        n.is_read = True
        db.commit()
        db.refresh(n)
    return n
