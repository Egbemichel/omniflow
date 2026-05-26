from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class FormStatus(str, Enum):
    uploaded = "UPLOADED"
    processing = "PROCESSING"
    ready = "READY"
    confirmed = "CONFIRMED"
    failed = "FAILED"


class FormFieldInput(BaseModel):
    field_name: str = Field(min_length=1)
    field_type: str = Field(default="text")
    required: bool = False
    position: int = Field(ge=0)


class FormFieldOut(FormFieldInput):
    id: Optional[str] = None

    model_config = {"from_attributes": True}


class FormUploadResponse(BaseModel):
    form_id: str
    status: FormStatus


class FormStatusResponse(BaseModel):
    form_id: str
    status: FormStatus
    field_count: int
    fields: Optional[List[FormFieldOut]] = None


class FormSchemaResponse(BaseModel):
    form_id: str
    status: FormStatus
    fields: List[FormFieldOut]


class FormSchemaUpdateRequest(BaseModel):
    fields: List[FormFieldInput]


class FormListItem(BaseModel):
    form_id: str
    original_filename: str
    status: FormStatus
    created_at: datetime
    updated_at: Optional[datetime]


class FormListResponse(BaseModel):
    page: int
    page_size: int
    total: int
    items: List[FormListItem]
