from fastapi import FastAPI
from app.database import Base, engine
from app.router import router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="OmniFlow Form Service", version="1.0.0")

app.include_router(router)


@app.get("/health")
def health():
    return {"status": "healthy", "service": "form"}
