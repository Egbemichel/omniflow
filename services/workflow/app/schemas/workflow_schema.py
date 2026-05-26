from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class WorkflowStatus(str, Enum):
    draft = "DRAFT"
    published = "PUBLISHED"


class Role(str, Enum):
    admin = "admin"
    staff = "staff"
    end_user = "end_user"


class StepCreate(BaseModel):
    step_name: str = Field(min_length=1)
    assigned_role: Role
    step_order: int = Field(ge=1)
    is_terminal: bool = False


class StepUpdate(BaseModel):
    step_name: Optional[str] = Field(default=None, min_length=1)
    assigned_role: Optional[Role] = None
    step_order: Optional[int] = Field(default=None, ge=1)
    is_terminal: Optional[bool] = None


class StepOut(BaseModel):
    id: str
    step_name: str
    assigned_role: Role
    step_order: int
    is_terminal: bool

    model_config = {"from_attributes": True}


class WorkflowCreate(BaseModel):
    name: str = Field(min_length=1)
    description: Optional[str] = None
    form_id: Optional[str] = None
    steps: Optional[List[StepCreate]] = None


class WorkflowUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1)
    description: Optional[str] = None
    form_id: Optional[str] = None


class WorkflowDetailResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    form_id: Optional[str]
    status: WorkflowStatus
    locked_at: Optional[datetime]
    steps: List[StepOut]

    model_config = {"from_attributes": True}


class WorkflowListItem(BaseModel):
    workflow_id: str
    name: str
    description: Optional[str] = None
    status: WorkflowStatus
    step_count: int
    created_at: datetime
    updated_at: Optional[datetime]


class WorkflowListResponse(BaseModel):
    page: int
    page_size: int
    total: int
    items: List[WorkflowListItem]
