from pydantic import BaseModel


class NotificationCreate(BaseModel):
    recipient_id: str
    event_type: str
    message: str


class NotificationOut(BaseModel):
    id: str
    recipient_id: str
    event_type: str
    message: str
    is_read: bool

    class Config:
        from_attributes = True
