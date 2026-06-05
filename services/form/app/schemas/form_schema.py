from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class FormStatus(str, Enum):
    uploaded = "UPLOADED"
    processing = "PROCESSING"
    ready = "READY"
    confirmed = "CONFIRMED"
    published = "PUBLISHED"
    failed = "FAILED"


class FormFieldInput(BaseModel):
    field_name: str = Field(min_length=1)
    field_type: str = Field(default="text")
    required: bool = False
    position: int = Field(ge=0)
    # Choices for select/radio/checkbox-group fields; null/empty for free text.
    options: Optional[List[str]] = None


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


# ---------------------------------------------------------------------------
# Submission schemas
# ---------------------------------------------------------------------------


class FieldValueInput(BaseModel):
    field_id: Optional[str] = None
    field_name: str = Field(min_length=1)
    value: Optional[str] = None


class SubmitFormRequest(BaseModel):
    submitter_id: Optional[str] = None
    field_values: List[FieldValueInput] = []


class SubmissionResponse(BaseModel):
    submission_id: str
    form_id: str
    status: str


class SubmissionItem(BaseModel):
    submission_id: str
    form_id: str
    submitter_id: str
    status: str
    submitted_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class SubmissionListResponse(BaseModel):
    page: int
    page_size: int
    total: int
    items: List[SubmissionItem]


class QRCodeResponse(BaseModel):
    form_id: str
    url: str
    qr_code_base64: str
