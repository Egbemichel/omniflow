# services/form/tests/conftest.py
import os
import sys
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# ---------------------------------------------------------------------------
# Path bootstrap
# ---------------------------------------------------------------------------
_TESTS_DIR = Path(__file__).resolve().parent
_FORM_ROOT = _TESTS_DIR.parent

if str(_FORM_ROOT) not in sys.path:
    sys.path.insert(0, str(_FORM_ROOT))

# ---------------------------------------------------------------------------
# Environment defaults (before app import so settings load cleanly)
# ---------------------------------------------------------------------------
os.environ.setdefault(
    "DATABASE_URL", "postgresql://pk_user:pk_password@localhost:5432/pk_user"
)
os.environ.setdefault("AUTH_SERVICE_URL", "http://auth:8001")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("MAX_FILE_SIZE_MB", "20")

# ---------------------------------------------------------------------------
# Local imports
# ---------------------------------------------------------------------------
from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models.form import Form, FormField  # noqa: F401, E402
from app.repositories.form_repository import FormRepository  # noqa: E402
from app.routes.dependencies import get_current_user  # noqa: E402

# ---------------------------------------------------------------------------
# Test database
# ---------------------------------------------------------------------------
DATABASE_URL = os.environ["DATABASE_URL"]
engine = create_engine(DATABASE_URL)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Session-scoped DB setup / teardown
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session", autouse=True)
def setup_db():
    app.dependency_overrides[get_db] = override_get_db
    yield
    engine.dispose()
    db_file = Path("test_form.db")
    if db_file.exists():
        try:
            db_file.unlink(missing_ok=True)
        except PermissionError:
            pass


# ---------------------------------------------------------------------------
# Per-test isolation
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def clean_db():
    yield
    with engine.begin() as conn:
        if engine.dialect.name == "postgresql":
            # PostgreSQL: Use TRUNCATE for speed and to reset sequences
            for table in reversed(Base.metadata.sorted_tables):
                schema_prefix = f"{table.schema}." if table.schema else ""
                conn.execute(
                    text(
                        f"TRUNCATE TABLE {schema_prefix}{table.name} RESTART IDENTITY CASCADE"
                    )
                )
        else:
            # SQLite: Use DELETE
            for table in reversed(Base.metadata.sorted_tables):
                conn.execute(table.delete())


# ---------------------------------------------------------------------------
# Core fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    # Ensure search_path is set for the session if using PostgreSQL
    if engine.dialect.name == "postgresql":
        db.execute(text("SET search_path TO form_schema"))
        db.commit()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def upload_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    return tmp_path


# ---------------------------------------------------------------------------
# Auth fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def admin_user():
    return {
        "user_id": 10,
        "email": "admin@pk.com",
        "role": "admin",
        "institution_id": 1,
    }


@pytest.fixture
def admin_client(admin_user):
    app.dependency_overrides[get_current_user] = lambda: admin_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def user_client():
    app.dependency_overrides[get_current_user] = lambda: {
        "user_id": 11,
        "email": "staff@pk.com",
        "role": "staff",
        "institution_id": 1,
    }
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def other_inst_client():
    """Client authenticated as admin of a different institution."""
    app.dependency_overrides[get_current_user] = lambda: {
        "user_id": 99,
        "email": "other@pk.com",
        "role": "admin",
        "institution_id": 2,
    }
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_current_user, None)


# ---------------------------------------------------------------------------
# Form factory
# ---------------------------------------------------------------------------
@pytest.fixture
def create_form(db_session):
    def _create(
        institution_id: int = 1,
        admin_id: int = 10,
        status: str = "READY",
        original_filename: str = "form.pdf",
    ):
        form_id = str(uuid.uuid4())
        repo = FormRepository(db_session)
        form = repo.create_form(
            form_id=form_id,
            institution_id=institution_id,
            admin_id=admin_id,
            original_filename=original_filename,
            file_path=f"/tmp/{form_id}.pdf",
            mime_type="application/pdf",
            status=status,
        )
        return form

    return _create
