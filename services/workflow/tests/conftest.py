import os
import sys
import uuid
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

_TESTS_DIR = Path(__file__).resolve().parent
_WORKFLOW_ROOT = _TESTS_DIR.parent

_s = str(_WORKFLOW_ROOT)
if _s not in sys.path:
    sys.path.insert(0, _s)

TEST_DB_URL = "sqlite:///./test_workflow.db"

os.environ.setdefault("DATABASE_URL", TEST_DB_URL)
os.environ.setdefault("AUTH_SERVICE_URL", "http://auth:8001")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

from app.main import app  # noqa: E402
from app.database import Base, get_db  # noqa: E402
from app.repositories.workflow_repository import WorkflowRepository  # noqa: E402
from app.routes.dependencies import get_current_user  # noqa: E402

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
    engine.dispose()
    db_file = Path("test_workflow.db")
    if db_file.exists():
        try:
            db_file.unlink()
        except PermissionError:
            pass


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
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def admin_user():
    return {
        "user_id": 42,
        "email": "admin@pk.com",
        "role": "admin",
        "institution_id": 1,
    }


@pytest.fixture
def staff_user():
    return {
        "user_id": 43,
        "email": "staff@pk.com",
        "role": "staff",
        "institution_id": 1,
    }


@pytest.fixture
def other_admin_user():
    return {
        "user_id": 99,
        "email": "admin@other.com",
        "role": "admin",
        "institution_id": 2,
    }


@pytest.fixture
def admin_client(admin_user):
    app.dependency_overrides[get_current_user] = lambda: admin_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def staff_client(staff_user):
    app.dependency_overrides[get_current_user] = lambda: staff_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def create_workflow(db_session):
    def _create(
        institution_id: int = 1,
        admin_id: int = 42,
        name: str = "Flow",
        description: str | None = None,
        form_id: str | None = None,
        status: str = "DRAFT",
    ):
        repo = WorkflowRepository(db_session)
        workflow_id = str(uuid.uuid4())
        workflow = repo.create_workflow(
            workflow_id=workflow_id,
            institution_id=institution_id,
            admin_id=admin_id,
            name=name,
            description=description,
            form_id=form_id,
        )
        if status == "PUBLISHED":
            repo.publish(workflow)
        return workflow

    return _create


@pytest.fixture
def add_step(db_session):
    def _add(
        workflow_id: str,
        step_name: str,
        assigned_role: str,
        step_order: int,
        is_terminal: bool = False,
    ):
        repo = WorkflowRepository(db_session)
        return repo.add_step(
            workflow_id=workflow_id,
            step_name=step_name,
            assigned_role=assigned_role,
            step_order=step_order,
            is_terminal=is_terminal,
        )

    return _add
