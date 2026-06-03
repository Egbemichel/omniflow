import os
import uuid
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.sql import func
from app.database import Base, DATABASE_URL


def _schema_name() -> str | None:
    if DATABASE_URL.startswith("sqlite"):
        return None
    return os.getenv("DATABASE_SCHEMA", "form_schema")


SCHEMA = _schema_name()


def _table_args() -> dict:
    return {"schema": SCHEMA} if SCHEMA else {}


def _form_fk() -> str:
    return f"{SCHEMA}.forms.id" if SCHEMA else "forms.id"


class Form(Base):
    __tablename__ = "forms"
    __table_args__ = _table_args()

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    institution_id = Column(Integer, nullable=False, index=True)
    admin_id = Column(String, nullable=False, index=True)
    original_filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    mime_type = Column(String, nullable=False)
    status = Column(String, nullable=False, default="UPLOADED")
    json_definition = Column(JSON, nullable=True)  # The extracted structure
    is_published = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class FormField(Base):
    __tablename__ = "form_fields"
    __table_args__ = _table_args()

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    form_id = Column(
        String, ForeignKey(_form_fk(), ondelete="CASCADE"), nullable=False, index=True
    )
    field_name = Column(String, nullable=False)
    field_type = Column(String, nullable=False, default="text")
    required = Column(Boolean, nullable=False, default=False)
    position = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
