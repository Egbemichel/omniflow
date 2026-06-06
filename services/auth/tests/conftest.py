# services/auth/tests/conftest.py
# Shared fixtures for ALL auth tests
import os
import sys
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# ---------------------------------------------------------------------------
# Path bootstrap — must happen before ANY local imports.
# services/auth/app/ is the actual package root (main.py lives there).
# ---------------------------------------------------------------------------
_TESTS_DIR = Path(__file__).resolve().parent  # …/services/auth/tests
_AUTH_ROOT = _TESTS_DIR.parent  # …/services/auth

_s = str(_AUTH_ROOT)
if _s not in sys.path:
    sys.path.insert(0, _s)

# ---------------------------------------------------------------------------
# Environment defaults — set before importing app so settings load cleanly.
# ---------------------------------------------------------------------------
os.environ.setdefault(
    "DATABASE_URL", "postgresql://pk_user:pk_password@localhost:5432/pk_user"
)
os.environ.setdefault("JWT_SECRET", "test_secret")
os.environ.setdefault("MAGIC_LINK_SECRET", "magic_secret")
os.environ.setdefault("MAGIC_LINK_TTL_SECONDS", "900")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("GOOGLE_CLIENT_ID", "test_google_id")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "test_google_secret")
os.environ.setdefault(
    "GOOGLE_REDIRECT_URI", "http://localhost/auth/oauth/google/callback"
)
os.environ.setdefault("GITHUB_CLIENT_ID", "test_github_id")
os.environ.setdefault("GITHUB_CLIENT_SECRET", "test_github_secret")

# ---------------------------------------------------------------------------
# Local imports — all resolved relative to services/auth/app/
# ---------------------------------------------------------------------------
from app.main import app  # noqa: E402
from app.database import Base, get_db  # noqa: E402
from app.models.user import User  # noqa: E402
from app.routes.dependencies import get_current_user  # noqa: E402
from app.routes.magic_link import get_magic_link_service  # noqa: E402
from app.services.magic_link_service import MagicLinkConfig, MagicLinkService  # noqa: E402

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
    """Database setup: Alembic migrations handle schema creation.
    This fixture exists only for cleanup after tests.
    """
    # Don't call Base.metadata.create_all() — Alembic handles it
    app.dependency_overrides[get_db] = override_get_db
    yield
    # Only drop tables on the local SQLite fast-path. NEVER drop the shared
    # Postgres schema — Alembic owns it, and dropping it breaks the running stack.
    if engine.dialect.name == "sqlite":
        Base.metadata.drop_all(bind=engine)
    engine.dispose()
    db_file = Path("test_auth.db")
    if db_file.exists():
        try:
            db_file.unlink()
        except PermissionError:
            pass


# ---------------------------------------------------------------------------
# Per-test isolation — wipe rows after every test
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def clean_db():
    """Wipe all rows between each test — guarantees full isolation."""
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
    """HTTP test client for the FastAPI app."""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def as_user():
    """Authenticate the test client as a given identity.

    The auth service issues JWTs and authenticates via ``Authorization: Bearer``
    (it does not trust gateway ``X-User-*`` headers like downstream services do).
    Per CLAUDE.md §7.4, tests override ``get_current_user`` rather than mocking the
    HTTP layer. Call this inside a test to install the override; it is removed
    automatically at teardown.
    """

    def _set(role: str = "admin", institution_id: int = 1, user_id: str = "admin-1"):
        identity = SimpleNamespace(
            id=user_id,
            email="actor@example.com",
            role=role,
            institution_id=institution_id,
            actor_type=None,
            is_active=True,
        )
        app.dependency_overrides[get_current_user] = lambda: identity
        return identity

    yield _set
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def db_session():
    """Bare DB session for direct model manipulation in tests."""
    db = TestingSessionLocal()
    # Ensure search_path is set for the session if using PostgreSQL
    if engine.dialect.name == "postgresql":
        db.execute(text("SET search_path TO auth_schema"))
        db.commit()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Magic Link helpers
# ---------------------------------------------------------------------------
class FakeRedis:
    """In-process Redis stand-in — no network required."""

    def __init__(self):
        self._store: dict[str, str] = {}

    def setex(self, key: str, ttl: int, value: str) -> None:
        self._store[key] = value

    def get(self, key: str) -> str | None:
        return self._store.get(key)

    def delete(self, key: str) -> None:
        self._store.pop(key, None)


@pytest.fixture
def fake_redis():
    """Standalone FakeRedis instance (useful when tests need direct access)."""
    return FakeRedis()


@pytest.fixture
def magic_link_service(fake_redis):
    """MagicLinkService wired to FakeRedis — no live Redis needed."""
    config = MagicLinkConfig(
        redis_url=os.environ["REDIS_URL"],
        secret=os.environ["MAGIC_LINK_SECRET"],
        ttl_seconds=int(os.environ["MAGIC_LINK_TTL_SECONDS"]),
    )
    return MagicLinkService(config, redis_client=fake_redis)


@pytest.fixture
def client_with_magic_link_override(magic_link_service):
    """HTTP client with MagicLinkService dependency overridden."""
    app.dependency_overrides[get_magic_link_service] = lambda: magic_link_service
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_magic_link_service, None)


# ---------------------------------------------------------------------------
# User factory
# ---------------------------------------------------------------------------
@pytest.fixture
def create_user():
    """Factory fixture — call inside a test to create a User row."""

    def _create(
        session,
        email: str = "test@example.com",
        role: str = "end_user",
        institution_id: int = 1,
        full_name: str = "Test User",
        oauth_provider: str = "test",
    ) -> User:
        user = User(
            email=email,
            full_name=full_name,
            role=role,
            institution_id=institution_id,
            oauth_provider=oauth_provider,
            oauth_id=str(uuid.uuid4()),
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user

    return _create
