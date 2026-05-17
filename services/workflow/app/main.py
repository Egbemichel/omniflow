from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app import models
from app.database import Base, engine
from app.routes.api import router
from app.services.event_service import EventService

Base.metadata.create_all(bind=engine)

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
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    try:
        EventService().ping()
    except Exception:
        pass


@app.get("/health")
def health():
    return {"status": "healthy", "service": "workflow"}
