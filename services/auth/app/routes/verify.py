from fastapi import APIRouter, Depends
from app.schemas.auth_schema import TokenVerifyResponse
from app.routes.dependencies import get_current_user

router = APIRouter()


@router.get("/auth/verify", response_model=TokenVerifyResponse)
def verify_token(current_user=Depends(get_current_user)):
    return {
        "user_id": current_user.id,
        "email": current_user.email,
        "role": current_user.role,
    }
