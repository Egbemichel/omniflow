from fastapi import FastAPI
from app.database import engine
from app.router import router
import os
from sqlalchemy import text

app = FastAPI(title="OmniFlow Task Service", version="1.0.0")


@app.on_event("startup")
async def startup_checks():
    schema = os.getenv("DATABASE_SCHEMA")
    if engine.dialect.name == "postgresql" and schema:
        with engine.connect() as conn:
            conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
            conn.commit()


app.include_router(router)


@app.get("/health")
def health():
    return {"status": "healthy", "service": "task"}
