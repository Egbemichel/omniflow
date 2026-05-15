# services/workflow/tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import Base, get_db

TEST_DB_URL = "sqlite:///./test_workflow.db"
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


@pytest.fixture
def admin_headers():
    """Mocked admin auth headers — workflow service trusts the gateway."""
    return {"X-User-Id": "admin-001", "X-User-Role": "admin"}


@pytest.fixture
def nurse_headers():
    return {"X-User-Id": "nurse-001", "X-User-Role": "nurse"}


@pytest.fixture
def doctor_headers():
    return {"X-User-Id": "doctor-001", "X-User-Role": "doctor"}


@pytest.fixture
def sample_workflow_payload():
    return {
        "name": "Patient Admission",
        "description": "Standard hospital admission workflow",
        "steps": [
            {"order": 1, "name": "Nurse Triage", "assigned_role": "nurse"},
            {"order": 2, "name": "Doctor Review", "assigned_role": "doctor"},
            {"order": 3, "name": "Admin Sign-off", "assigned_role": "admin"},
        ],
    }


@pytest.fixture
def draft_workflow(client, admin_headers, sample_workflow_payload):
    """Creates a draft workflow and returns it."""
    response = client.post(
        "/workflows", json=sample_workflow_payload, headers=admin_headers
    )
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def published_workflow(client, admin_headers, draft_workflow):
    """Creates and publishes a workflow."""
    wf_id = draft_workflow["id"]
    client.post(f"/workflows/{wf_id}/publish", headers=admin_headers)
    response = client.get(f"/workflows/{wf_id}", headers=admin_headers)
    return response.json()
