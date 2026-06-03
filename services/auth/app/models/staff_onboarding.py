import os
import uuid
from sqlalchemy import Column, DateTime, Integer, String, JSON, ForeignKey
from sqlalchemy.sql import func
from app.database import Base, DATABASE_URL


def _schema_name() -> str | None:
    if DATABASE_URL.startswith("sqlite"):
        return None
    return os.getenv("DATABASE_SCHEMA", "auth_schema")


SCHEMA = _schema_name()


def _table_args() -> dict:
    return {"schema": SCHEMA} if SCHEMA else {}


class UploadStatus:
    PENDING = "pending"
    PROCESSED = "processed"
    FAILED = "failed"


class StaffCSVUpload(Base):
    __tablename__ = "staff_csv_uploads"
    __table_args__ = _table_args()

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    institution_id = Column(Integer, nullable=False, index=True)
    uploaded_by = Column(String, nullable=False)  # user_id
    file_name = Column(String, nullable=False)
    raw_content = Column(String, nullable=True)
    parsed_rows = Column(JSON, nullable=True)
    row_count = Column(Integer, default=0)
    upload_status = Column(String, default=UploadStatus.PENDING)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class StaffCSVRow(Base):
    __tablename__ = "staff_csv_rows"
    __table_args__ = _table_args()

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    upload_id = Column(
        String,
        ForeignKey(
            f"{SCHEMA}.staff_csv_uploads.id" if SCHEMA else "staff_csv_uploads.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )
    institution_id = Column(Integer, nullable=False, index=True)
    email = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    role = Column(String, nullable=False)
    department = Column(String, nullable=True)
    extra_fields = Column(JSON, nullable=True)
    matched_user_id = Column(String, nullable=True)  # Set when user logs in
    created_at = Column(DateTime(timezone=True), server_default=func.now())
