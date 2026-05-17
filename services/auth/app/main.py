from fastapi import FastAPI
from app import models
from app.database import Base, engine
from app.routes.api import router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="OmniFlow Auth Service", version="1.0.0")

app.include_router(router)


@app.get("/health")
def health():
    return {"status": "healthy", "service": "auth"}
