from fastapi import APIRouter
from app.routes import forms, upload

router = APIRouter()
router.include_router(upload.router)
router.include_router(forms.router)
