from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.database import engine
from app.router import router
from app.sse import router as sse_router
from app.worker import start_worker
import os
from sqlalchemy import text


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure schema exists and start worker
    schema = os.getenv("DATABASE_SCHEMA", "notification_schema")
    if engine.dialect.name == "postgresql" and schema:
        with engine.connect() as conn:
            conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
            conn.commit()

    # Start the background subscriber
    start_worker()
    yield
    # Shutdown logic if needed


app = FastAPI(title="OmniFlow Notification Service", version="1.0.0", lifespan=lifespan)


app.include_router(router)
app.include_router(sse_router)


@app.get("/health")
def health():
    return {"status": "healthy", "service": "notification"}
