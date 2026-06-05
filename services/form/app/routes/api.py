from fastapi import APIRouter
from app.routes import forms, submissions, upload

router = APIRouter()
router.include_router(upload.router)
router.include_router(forms.router)
router.include_router(submissions.router)
