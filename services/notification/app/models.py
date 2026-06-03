import os
import uuid
from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.sql import func
from app.database import Base, DATABASE_URL


def _schema_name() -> str | None:
    if DATABASE_URL.startswith("sqlite"):
        return None
    return os.getenv("DATABASE_SCHEMA", "notification_schema")


SCHEMA = _schema_name()


def _table_args() -> dict:
    return {"schema": SCHEMA} if SCHEMA else {}


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = _table_args()

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    institution_id = Column(Integer, nullable=False, index=True, default=1)
    recipient_id = Column(String, nullable=False, index=True)
    event_type = Column(
        String, nullable=False
    )  # task_assigned | submission_completed | form_ready
    message = Column(String, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
