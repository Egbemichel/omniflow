from pydantic import BaseModel
from typing import Optional, Dict, Any


class SubmissionCreate(BaseModel):
    workflow_id: str
    form_data: Dict[str, Any] = {}


class SubmissionOut(BaseModel):
    id: str
    workflow_id: str
    submitted_by: str
    status: str

    class Config:
        from_attributes = True


class SubmissionStatusOut(BaseModel):
    id: str
    status: str
    current_step: Optional[int] = None
    assigned_role: Optional[str] = None

    class Config:
        from_attributes = True


class TaskOut(BaseModel):
    id: str
    submission_id: str
    assigned_role: str
    status: str

    class Config:
        from_attributes = True


class AuditEventOut(BaseModel):
    id: str
    submission_id: str
    action: str
    actor_id: str
    actor_role: Optional[str]

    class Config:
        from_attributes = True
