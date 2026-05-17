# services/workflow/tests/conftest.py
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

# ---------------------------------------------------------------------------
# Path bootstrap
# ---------------------------------------------------------------------------
_TESTS_DIR = Path(__file__).resolve().parent
_APP_ROOT = _TESTS_DIR.parent / "app"

if str(_APP_ROOT.parent) not in sys.path:
    sys.path.insert(0, str(_APP_ROOT.parent))

# ---------------------------------------------------------------------------
# Environment defaults
# ---------------------------------------------------------------------------
os.environ.setdefault("JWT_SECRET", "test_secret")
os.environ.setdefault("AUTH_SERVICE_URL", "http://localhost:8000")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

# ---------------------------------------------------------------------------
# Local imports
# ---------------------------------------------------------------------------
from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models.workflow import Workflow, WorkflowStep  # noqa: F401, E402

# ---------------------------------------------------------------------------
# SQLite test DB — strip schema prefixes so SQLite doesn't choke on
# "CREATE TABLE workflow.workflows" (SQLite has no schema support).
# ---------------------------------------------------------------------------
TEST_DB_URL = "sqlite:///./test_workflow.db"

engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})


def _strip_schema(target, connection, **kw):
    """Remove schema from table name before SQLite DDL executes."""
    target.schema = None


# Apply the schema-stripping listener to every Table in metadata
for table in Base.metadata.tables.values():
    event.listen(table, "before_create", _strip_schema)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Auth dependency override — no live Auth Service needed in tests
# ---------------------------------------------------------------------------
ADMIN_USER = {"id": 1, "email": "admin@test.com", "role": "admin", "institution_id": 1}
STAFF_USER = {"id": 2, "email": "staff@test.com", "role": "staff", "institution_id": 1}
OTHER_INST_USER = {
    "id": 3,
    "email": "other@test.com",
    "role": "admin",
    "institution_id": 2,
}


def make_auth_override(user: dict):
    def _override():
        return user

    return _override


# ---------------------------------------------------------------------------
# Session-scoped DB setup / teardown
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session", autouse=True)
def setup_db():
    """Create all tables once, drop after session."""
    # Re-strip schema on all tables in case metadata was re-imported
    for table in Base.metadata.tables.values():
        table.schema = None

    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    yield
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    db_file = Path("test_workflow.db")
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
    """HTTP client authenticated as admin (institution_id=1)."""
    from app.routes.dependencies import get_current_user

    app.dependency_overrides[get_current_user] = make_auth_override(ADMIN_USER)
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def staff_client():
    """HTTP client authenticated as staff (institution_id=1)."""
    from app.routes.dependencies import get_current_user

    app.dependency_overrides[get_current_user] = make_auth_override(STAFF_USER)
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def other_inst_client():
    """HTTP client authenticated as admin of a different institution."""
    from app.routes.dependencies import get_current_user

    app.dependency_overrides[get_current_user] = make_auth_override(OTHER_INST_USER)
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Workflow factory helpers
# ---------------------------------------------------------------------------
@pytest.fixture
def create_workflow():
    """Factory: create a workflow row directly in the DB."""

    def _create(
        session,
        name: str = "Test Workflow",
        institution_id: int = 1,
        admin_id: int = 1,
        status: str = "DRAFT",
    ) -> Workflow:
        import uuid

        wf = Workflow(
            id=str(uuid.uuid4()),
            name=name,
            institution_id=institution_id,
            admin_id=admin_id,
            status=status,
        )
        session.add(wf)
        session.commit()
        session.refresh(wf)
        return wf

    return _create


@pytest.fixture
def create_step():
    """Factory: create a workflow step row directly in the DB."""

    def _create(
        session,
        workflow_id: str,
        step_name: str = "Review",
        assigned_role: str = "staff",
        step_order: int = 1,
        is_terminal: bool = True,
    ) -> WorkflowStep:
        import uuid

        step = WorkflowStep(
            id=str(uuid.uuid4()),
            workflow_id=workflow_id,
            step_name=step_name,
            assigned_role=assigned_role,
            step_order=step_order,
            is_terminal=is_terminal,
        )
        session.add(step)
        session.commit()
        session.refresh(step)
        return step

    return _create
