from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app import models  # noqa: F401  # registers models with Base.metadata
from app.database import engine, SessionLocal
from app.routes.api import router
from app.services.event_service import EventService
from app.schema_utils import validate_schema_isolation

app = FastAPI(title="OmniFlow Workflow Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.on_event("startup")
def startup_checks():
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))

        # Verify schema isolation (PostgreSQL only)
        if engine.dialect.name == "postgresql":
            validate_schema_isolation(db, "workflow_schema", "workflow")

        EventService().ping()
    except Exception as e:
        print(f"Startup check failed: {e}")
    finally:
        db.close()


@app.get("/health")
def health():
    return {"status": "healthy", "service": "workflow"}
