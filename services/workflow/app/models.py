import uuid
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Workflow(Base):
    __tablename__ = "workflows"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    status = Column(String, nullable=False, default="draft")  # draft | published
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    steps = relationship("WorkflowStep", back_populates="workflow", order_by="WorkflowStep.order", cascade="all, delete-orphan")
    submission_states = relationship("SubmissionState", back_populates="workflow", cascade="all, delete-orphan")


class WorkflowStep(Base):
    __tablename__ = "workflow_steps"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_id = Column(String, ForeignKey("workflows.id"), nullable=False)
    order = Column(Integer, nullable=False)
    name = Column(String, nullable=False)
    assigned_role = Column(String, nullable=False)

    workflow = relationship("Workflow", back_populates="steps")


class SubmissionState(Base):
    __tablename__ = "submission_states"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    submission_id = Column(String, nullable=False, unique=True, index=True)
    workflow_id = Column(String, ForeignKey("workflows.id"), nullable=False)
    current_step = Column(Integer, nullable=True)  # None when completed
    status = Column(String, nullable=False, default="in_progress")  # in_progress | completed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    workflow = relationship("Workflow", back_populates="submission_states")
