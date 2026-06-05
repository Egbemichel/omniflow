from enum import Enum

from pydantic import BaseModel, Field


class SystemRole(str, Enum):
    admin = "admin"
    staff = "staff"
    end_user = "end_user"


class ActorTypeCreate(BaseModel):
    label: str = Field(min_length=1, max_length=120)
    system_role: SystemRole = SystemRole.staff


class ActorTypeResponse(BaseModel):
    id: str
    institution_id: int
    label: str
    system_role: str

    model_config = {"from_attributes": True}
