# services/auth/tests/conftest.py
# Shared fixtures for ALL auth tests
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import Base, get_db

# Use an in-memory SQLite DB for fast unit tests
# (Integration tests use real postgres via env var)
TEST_DB_URL = "sqlite:///./test_auth.db"

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
    """Create all tables once for the test session, drop after."""
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(autouse=True)
def clean_db():
    """Wipe all tables between each test — guarantees isolation."""
    yield
    with engine.connect() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
        conn.commit()

@pytest.fixture
def client():
    """HTTP test client for making requests to the FastAPI app."""
    with TestClient(app) as c:
        yield c

@pytest.fixture
def register_user(client):
    """Helper: registers and returns a user dict."""
    def _register(email="test@example.com", password="SecurePass123!", role="end_user"):
        response = client.post("/auth/register", json={
            "email": email,
            "password": password,
            "full_name": "Test User",
            "role": role
        })
        return response
    return _register

@pytest.fixture
def logged_in_user(client, register_user):
    """Helper: registers then logs in, returns token."""
    register_user()
    response = client.post("/auth/login", json={
        "email": "test@example.com",
        "password": "SecurePass123!"
    })
    return {
        "token": response.json()["access_token"],
        "email": "test@example.com"
    }

@pytest.fixture
def admin_token(client, register_user):
    """Helper: creates an admin user and returns their token."""
    register_user(email="admin@pk.com", role="admin")
    response = client.post("/auth/login", json={
        "email": "admin@pk.com",
        "password": "SecurePass123!"
    })
    return response.json()["access_token"]

