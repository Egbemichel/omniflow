from pydantic import BaseModel
from typing import List, Dict, Any, Optional


class FormOut(BaseModel):
    id: str
    name: str
    status: str
    fields: List[Dict[str, Any]]
    uploaded_by: str

    class Config:
        from_attributes = True


class FieldUpdate(BaseModel):
    fields: List[Dict[str, Any]]
