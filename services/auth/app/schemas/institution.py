from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class InstitutionBase(BaseModel):
    name: str
    type: str


class InstitutionCreate(InstitutionBase):
    pass


class InstitutionUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None


class InstitutionResponse(InstitutionBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
