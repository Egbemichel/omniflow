from fastapi import APIRouter
from app.routes import steps, workflows, transition

router = APIRouter()
router.include_router(workflows.router)
router.include_router(steps.router)
router.include_router(transition.router)
