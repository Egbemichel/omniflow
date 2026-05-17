import os
import uuid
from sqlalchemy import Boolean, Column, DateTime, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base, DATABASE_URL


def _schema_name() -> str | None:
    if DATABASE_URL.startswith("sqlite"):
        return None
    return os.getenv("WORKFLOW_SCHEMA", "workflow")


SCHEMA = _schema_name()


def _table_args() -> dict:
    return {"schema": SCHEMA} if SCHEMA else {}


def _workflow_fk() -> str:
    return f"{SCHEMA}.workflows.id" if SCHEMA else "workflows.id"


class Workflow(Base):
    __tablename__ = "workflows"
    __table_args__ = _table_args()

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    institution_id = Column(Integer, nullable=False, index=True)
    admin_id = Column(Integer, nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    form_id = Column(String, nullable=True)
    status = Column(String, nullable=False, default="DRAFT")
    locked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    steps = relationship(
        "WorkflowStep",
        back_populates="workflow",
        order_by="WorkflowStep.step_order",
        cascade="all, delete-orphan",
    )


class WorkflowStep(Base):
    __tablename__ = "workflow_steps"
    __table_args__ = _table_args()

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_id = Column(String, ForeignKey(_workflow_fk(), ondelete="CASCADE"), nullable=False)
    step_name = Column(String, nullable=False)
    assigned_role = Column(String, nullable=False)
    step_order = Column(Integer, nullable=False)
    is_terminal = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    workflow = relationship("Workflow", back_populates="steps")
