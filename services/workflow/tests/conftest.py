# services/workflow/tests/conftest.py
import os
import sys
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

# ---------------------------------------------------------------------------
# Path bootstrap
# ---------------------------------------------------------------------------
_TESTS_DIR = Path(__file__).resolve().parent
_APP_ROOT = _TESTS_DIR.parent

if str(_APP_ROOT) not in sys.path:
    sys.path.insert(0, str(_APP_ROOT))

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
from app.routes.dependencies import get_current_user  # noqa: E402

# ---------------------------------------------------------------------------
# SQLite test DB — strip schema prefixes (SQLite has no schema support)
# ---------------------------------------------------------------------------
TEST_DB_URL = "sqlite:///./test_workflow.db"

engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})


def _strip_schema(target, connection, **kw):
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
# User stubs
# ---------------------------------------------------------------------------
ADMIN_USER = {"id": 1, "email": "admin@test.com", "role": "admin", "institution_id": 1}
STAFF_USER = {"id": 2, "email": "staff@test.com", "role": "staff", "institution_id": 1}
OTHER_INST_USER = {
    "id": 3,
    "email": "other@test.com",
    "role": "admin",
    "institution_id": 2,
}


# ---------------------------------------------------------------------------
# Session-scoped DB setup / teardown
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session", autouse=True)
def setup_db():
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
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client():
    """Unauthenticated client."""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def admin_client():
    """HTTP client authenticated as admin (institution_id=1)."""
    app.dependency_overrides[get_current_user] = lambda: ADMIN_USER
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def staff_client():
    """HTTP client authenticated as staff (institution_id=1)."""
    app.dependency_overrides[get_current_user] = lambda: STAFF_USER
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def other_inst_client():
    """HTTP client authenticated as admin of a different institution."""
    app.dependency_overrides[get_current_user] = lambda: OTHER_INST_USER
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_current_user, None)


# ---------------------------------------------------------------------------
# Workflow factory
# ---------------------------------------------------------------------------
@pytest.fixture
def create_workflow():
    """Factory: create a workflow row directly in the DB."""

    def _create(
        institution_id: int = 1,
        admin_id: int = 1,
        name: str = "Test Workflow",
        status: str = "DRAFT",
    ) -> Workflow:
        db = TestingSessionLocal()
        try:
            wf = Workflow(
                id=str(uuid.uuid4()),
                name=name,
                institution_id=institution_id,
                admin_id=admin_id,
                status=status,
            )
            db.add(wf)
            db.commit()
            db.refresh(wf)
            return wf
        finally:
            db.close()

    return _create


# ---------------------------------------------------------------------------
# Step factory (used by test_publish.py and test_steps.py as "add_step")
# ---------------------------------------------------------------------------
@pytest.fixture
def add_step():
    """Factory: create a workflow step row directly in the DB."""

    def _create(
        workflow_id: str,
        step_name: str = "Review",
        assigned_role: str = "staff",
        step_order: int = 1,
        is_terminal: bool = True,
    ) -> WorkflowStep:
        db = TestingSessionLocal()
        try:
            step = WorkflowStep(
                id=str(uuid.uuid4()),
                workflow_id=workflow_id,
                step_name=step_name,
                assigned_role=assigned_role,
                step_order=step_order,
                is_terminal=is_terminal,
            )
            db.add(step)
            db.commit()
            db.refresh(step)
            return step
        finally:
            db.close()

    return _create


# ---------------------------------------------------------------------------
# Alias so tests using "create_step" also work
# ---------------------------------------------------------------------------
@pytest.fixture
def create_step(add_step):
    return add_step
