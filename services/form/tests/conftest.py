import os
import sys
import uuid
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

_TESTS_DIR = Path(__file__).resolve().parent
_FORM_ROOT = _TESTS_DIR.parent

_s = str(_FORM_ROOT)
if _s not in sys.path:
    sys.path.insert(0, _s)

TEST_DB_URL = "sqlite:///./test_form.db"

os.environ.setdefault("DATABASE_URL", TEST_DB_URL)
os.environ.setdefault("AUTH_SERVICE_URL", "http://auth:8001")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("MAX_FILE_SIZE_MB", "20")

from app.main import app  # noqa: E402
from app.database import Base, get_db  # noqa: E402
from app.routes.dependencies import get_current_user  # noqa: E402
from app.repositories.form_repository import FormRepository  # noqa: E402

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
    db_file = Path("test_form.db")
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
def upload_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    return tmp_path


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
