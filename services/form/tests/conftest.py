# services/form/tests/conftest.py
import os
import sys
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
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
TEST_DB_URL = "sqlite:///./test_form.db"

os.environ.setdefault("DATABASE_URL", TEST_DB_URL)
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
# SQLite test DB — strip schema prefixes so SQLite doesn't choke on
# "CREATE TABLE form.forms" (SQLite has no schema support).
# ---------------------------------------------------------------------------
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})


def _strip_schema(target, connection, **kw):
    """Null out schema before SQLite DDL so it doesn't generate 'form.forms'."""
    if connection.engine.dialect.name == "sqlite":
        target.schema = None


for _table in Base.metadata.tables.values():
    event.listen(_table, "before_create", _strip_schema)

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
    if engine.dialect.name == "sqlite":
        # Null schema directly as well, in case listener fires after re-import
        for table in Base.metadata.tables.values():
            table.schema = None
    else:
        # For PostgreSQL, ensure schema exists and search_path is set
        with engine.connect() as conn:
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS form_schema"))
            conn.execute(text("SET search_path TO form_schema"))
            conn.commit()

    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    yield
    if engine.dialect.name == "sqlite":
        Base.metadata.drop_all(bind=engine)
    engine.dispose()
    db_file = Path("test_form.db")
    if db_file.exists():
        db_file.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Per-test isolation
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def clean_db():
    yield
    with engine.connect() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
        conn.commit()


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
