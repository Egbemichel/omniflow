from fastapi import FastAPI
from sqlalchemy import text
from app import models  # noqa: F401
from app.database import engine, SessionLocal
from app.routes.api import router
from app.schema_utils import validate_schema_isolation
from app.services.bootstrap_service import (
    bootstrap_super_admin,
    ensure_default_institution,
)

app = FastAPI(title="OmniFlow Auth Service", version="1.0.0")

app.include_router(router)


@app.on_event("startup")
def startup_checks():
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))

        # Verify schema isolation (PostgreSQL only)
        if engine.dialect.name == "postgresql":
            validate_schema_isolation(db, "auth_schema", "auth")
        ensure_default_institution(db)
        bootstrap_super_admin(db)
    except Exception as e:
        print(f"Startup check failed: {e}")
    finally:
        db.close()


@app.get("/health")
def health():
    return {"status": "healthy", "service": "auth"}
