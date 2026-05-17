import uuid
from sqlalchemy import Boolean, Column, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("oauth_provider", "oauth_id", name="uq_oauth"),)

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False, index=True)
    full_name = Column(String, nullable=True)
    role = Column(String, nullable=False, default="end_user")
    institution_id = Column(Integer, nullable=False, default=1, index=True)
    is_active = Column(Boolean, default=True)
    oauth_provider = Column(String, nullable=True, index=True)
    oauth_id = Column(String, nullable=True, index=True)
    last_login = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
