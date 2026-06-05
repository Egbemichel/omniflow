import os
import uuid
from sqlalchemy import Boolean, Column, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.sql import func
from app.database import Base, DATABASE_URL


def _schema_name() -> str | None:
    if DATABASE_URL.startswith("sqlite"):
        return None
    return os.getenv("DATABASE_SCHEMA", "auth_schema")


SCHEMA = _schema_name()


def _table_args() -> tuple:
    args = (UniqueConstraint("oauth_provider", "oauth_id", name="uq_oauth"),)
    if SCHEMA:
        return args + ({"schema": SCHEMA},)
    return args


class User(Base):
    __tablename__ = "users"
    __table_args__ = _table_args()

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False, index=True)
    full_name = Column(String, nullable=True)
    role = Column(String, nullable=False, default="end_user")
    actor_type = Column(String, nullable=True)
    institution_id = Column(Integer, nullable=False, default=1, index=True)
    is_active = Column(Boolean, default=True)
    oauth_provider = Column(String, nullable=True, index=True)
    oauth_id = Column(String, nullable=True, index=True)
    last_login = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
