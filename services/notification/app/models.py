import uuid
from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.database import Base
from app.schema_utils import _schema_name


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = {"schema": _schema_name()}

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    recipient_id = Column(String, nullable=False, index=True)
    event_type = Column(
        String, nullable=False
    )  # task_assigned | submission_completed | form_ready
    message = Column(String, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
