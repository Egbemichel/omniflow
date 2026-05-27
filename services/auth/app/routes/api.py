from fastapi import APIRouter
from app.routes import admin, magic_link, oauth, passkeys, verify

router = APIRouter()
router.include_router(oauth.router, prefix="/auth")
router.include_router(magic_link.router, prefix="/auth")
router.include_router(passkeys.router)
router.include_router(verify.router)
router.include_router(admin.router)
