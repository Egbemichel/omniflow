import os
import uuid
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func
from app.database import Base, DATABASE_URL


def _schema_name() -> str | None:
    if DATABASE_URL.startswith("sqlite"):
        return None
    return os.getenv("DATABASE_SCHEMA", "form_schema")


SCHEMA = _schema_name()


def _table_args() -> dict:
    return {"schema": SCHEMA} if SCHEMA else {}


def _forms_fk() -> str:
    return f"{SCHEMA}.forms.id" if SCHEMA else "forms.id"


def _form_fields_fk() -> str:
    return f"{SCHEMA}.form_fields.id" if SCHEMA else "form_fields.id"


def _form_submissions_fk() -> str:
    return f"{SCHEMA}.form_submissions.id" if SCHEMA else "form_submissions.id"


class FormSubmission(Base):
    __tablename__ = "form_submissions"
    __table_args__ = _table_args()

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    form_id = Column(
        String,
        ForeignKey(_forms_fk(), ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    institution_id = Column(Integer, nullable=False, index=True)
    submitter_id = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, default="SUBMITTED")
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class FormFieldValue(Base):
    __tablename__ = "form_field_values"
    __table_args__ = _table_args()

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    submission_id = Column(
        String,
        ForeignKey(_form_submissions_fk(), ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    field_id = Column(
        String,
        ForeignKey(_form_fields_fk(), ondelete="SET NULL"),
        nullable=True,
    )
    field_name = Column(String, nullable=False)
    value = Column(Text, nullable=True)
