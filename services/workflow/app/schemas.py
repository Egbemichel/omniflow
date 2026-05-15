from pydantic import BaseModel, field_validator
from typing import List, Optional


class StepIn(BaseModel):
    order: int
    name: str
    assigned_role: str


class WorkflowCreate(BaseModel):
    name: str
    description: Optional[str] = None
    steps: List[StepIn]

    @field_validator("steps")
    @classmethod
    def steps_not_empty(cls, v):
        if not v:
            raise ValueError("Workflow must have at least one step")
        return v


class StepOut(BaseModel):
    id: str
    order: int
    name: str
    assigned_role: str

    class Config:
        from_attributes = True


class WorkflowOut(BaseModel):
    id: str
    name: str
    description: Optional[str]
    status: str
    steps: List[StepOut]

    class Config:
        from_attributes = True


class InitialiseRequest(BaseModel):
    submission_id: str


class TransitionRequest(BaseModel):
    submission_id: str


class SubmissionStateOut(BaseModel):
    submission_id: str
    workflow_id: str
    current_step: Optional[int]
    status: str
    assigned_role: Optional[str] = None

    class Config:
        from_attributes = True
