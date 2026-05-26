import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.schema_utils import validate_schema_isolation

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./notification.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    # Call isolation validation on every get_db (covers schema_utils)
    if not DATABASE_URL.startswith("sqlite"):
        validate_schema_isolation(db)
    try:
        yield db
    finally:
        db.close()
