import uuid
from sqlalchemy import Column, String, DateTime, JSON
from sqlalchemy.sql import func
from app.database import Base


class Form(Base):
    __tablename__ = "forms"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    file_path = Column(String, nullable=True)
    fields = Column(JSON, nullable=False, default=list)  # extracted field definitions
    status = Column(String, nullable=False, default="processing")  # processing | ready | error
    uploaded_by = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
