import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os

from app.main import app
from app.database import Base, get_db
from app.models import SCHEMA

# Force tests to use PostgreSQL if available, else SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test_notification.db")
engine = create_engine(DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    if not DATABASE_URL.startswith("sqlite") and SCHEMA:
        db.execute(text(f"SET search_path TO {SCHEMA}"))
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    if not DATABASE_URL.startswith("sqlite") and SCHEMA:
        with engine.connect() as conn:
            conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}"))
            conn.commit()

    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    yield


@pytest.fixture(autouse=True)
def clean_db():
    yield
    with engine.connect() as conn:
        if not DATABASE_URL.startswith("sqlite") and SCHEMA:
            conn.execute(text(f"SET search_path TO {SCHEMA}"))

        for table in reversed(Base.metadata.sorted_tables):
            if DATABASE_URL.startswith("sqlite"):
                conn.execute(table.delete())
            else:
                table_name = table.name
                conn.execute(
                    text(f'TRUNCATE TABLE "{table_name}" RESTART IDENTITY CASCADE')
                )
        conn.commit()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
