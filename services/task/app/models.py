import os
import uuid
from sqlalchemy import Column, String, DateTime, JSON
from sqlalchemy.sql import func
from app.database import Base, DATABASE_URL


def _schema_name() -> str | None:
    if DATABASE_URL.startswith("sqlite"):
        return None
    return os.getenv("DATABASE_SCHEMA", "task_schema")


SCHEMA = _schema_name()


def _table_args() -> dict:
    return {"schema": SCHEMA} if SCHEMA else {}


class Submission(Base):
    __tablename__ = "submissions"
    __table_args__ = _table_args()

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_id = Column(String, nullable=False, index=True)
    submitted_by = Column(String, nullable=False, index=True)  # user_id from header
    form_data = Column(JSON, nullable=False, default=dict)
    status = Column(
        String, nullable=False, default="in_progress"
    )  # in_progress | completed
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = _table_args()

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    submission_id = Column(String, nullable=False, index=True)
    assigned_role = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, default="pending")  # pending | completed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    completed_by = Column(String, nullable=True)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = _table_args()

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    submission_id = Column(String, nullable=False, index=True)
    action = Column(String, nullable=False)
    actor_id = Column(String, nullable=False)
    actor_role = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
