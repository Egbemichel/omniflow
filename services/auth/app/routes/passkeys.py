from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.get("/auth/passkeys")
def passkeys_stub():
    raise HTTPException(status_code=501, detail="Coming soon")
