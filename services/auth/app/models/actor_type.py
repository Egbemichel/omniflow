import os
import uuid

from sqlalchemy import Column, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.sql import func

from app.database import Base, DATABASE_URL


def _schema_name() -> str | None:
    if DATABASE_URL.startswith("sqlite"):
        return None
    return os.getenv("DATABASE_SCHEMA", "auth_schema")


SCHEMA = _schema_name()


def _table_args() -> tuple:
    args = (UniqueConstraint("institution_id", "label", name="uq_actor_type_label"),)
    if SCHEMA:
        return args + ({"schema": SCHEMA},)
    return args


class ActorType(Base):
    """An institution-defined workflow actor label (e.g. "Triage Nurse").

    Each actor type maps to a system role. By default that is ``staff``, but an
    admin may map an actor type to any system role.
    """

    __tablename__ = "actor_types"
    __table_args__ = _table_args()

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    institution_id = Column(Integer, nullable=False, index=True)
    label = Column(String, nullable=False)
    system_role = Column(String, nullable=False, default="staff")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
