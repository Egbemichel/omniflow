from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    full_name: Optional[str]
    role: str
    institution_id: int
    is_active: bool
    oauth_provider: Optional[str]
    oauth_id: Optional[str]
    last_login: Optional[datetime]

    model_config = {"from_attributes": True}


class RoleAssign(BaseModel):
    role: str
