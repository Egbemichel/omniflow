from fastapi import APIRouter
from app.routes import steps, workflows

router = APIRouter()
router.include_router(workflows.router)
router.include_router(steps.router)
