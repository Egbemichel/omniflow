# services/task/tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch
from app.main import app
from app.database import Base, get_db
import os
from sqlalchemy import text

TEST_DB_URL = "sqlite:///./test_task.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    if engine.dialect.name == "sqlite":
        for table in Base.metadata.tables.values():
            table.schema = None
    else:
        schema = os.getenv("DATABASE_SCHEMA", "task_schema")
        with engine.connect() as conn:
            conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
            conn.execute(text(f"SET search_path TO {schema}"))
            conn.commit()

    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def clean_db():
    yield
    with engine.connect() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
        conn.commit()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


# Mock the Workflow Service HTTP call so task tests don't need it running
@pytest.fixture
def mock_workflow_service():
    with (
        patch("app.services.workflow_client.initialise_submission") as mock_init,
        patch("app.services.workflow_client.advance_submission") as mock_advance,
    ):
        mock_init.return_value = {
            "submission_id": "sub-001",
            "current_step": 1,
            "assigned_role": "nurse",
            "status": "in_progress",
        }
        mock_advance.return_value = {
            "submission_id": "sub-001",
            "current_step": 2,
            "assigned_role": "doctor",
            "status": "in_progress",
        }
        yield {"init": mock_init, "advance": mock_advance}


@pytest.fixture
def nurse_headers():
    return {"X-User-Id": "nurse-001", "X-User-Role": "nurse"}


@pytest.fixture
def doctor_headers():
    return {"X-User-Id": "doctor-001", "X-User-Role": "doctor"}


@pytest.fixture
def end_user_headers():
    return {"X-User-Id": "user-001", "X-User-Role": "end_user"}


@pytest.fixture
def created_submission(client, end_user_headers, mock_workflow_service):
    response = client.post(
        "/submissions",
        json={
            "workflow_id": "wf-001",
            "form_data": {"patient_name": "John Doe", "age": "35"},
        },
        headers=end_user_headers,
    )
    assert response.status_code == 201
    return response.json()
