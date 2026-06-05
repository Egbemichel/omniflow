from pydantic import BaseModel, model_validator
from typing import Optional, Dict, Any


class SubmissionCreate(BaseModel):
    # Either the workflow is named directly, or a form_id is given and the
    # workflow is resolved from it (public QR submissions take the form_id path).
    workflow_id: Optional[str] = None
    form_id: Optional[str] = None
    form_data: Dict[str, Any] = {}
    submitter_id: Optional[str] = None

    @model_validator(mode="after")
    def _require_target(self):
        if not self.workflow_id and not self.form_id:
            raise ValueError("workflow_id or form_id is required")
        return self


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
    current_step_id: Optional[str] = None
    assigned_role: Optional[str] = None
    form_id: Optional[str] = None
    form_data: Dict[str, Any] = {}

    class Config:
        from_attributes = True


class FormDataUpdate(BaseModel):
    form_data: Dict[str, Any]


class TaskOut(BaseModel):
    id: str
    submission_id: str
    assigned_role: str
    actor_type: Optional[str] = None
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
