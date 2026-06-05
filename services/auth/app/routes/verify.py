from fastapi import APIRouter, Depends, Response
from app.schemas.auth_schema import TokenVerifyResponse
from app.routes.dependencies import get_current_user

router = APIRouter()


@router.get("/auth/verify", response_model=TokenVerifyResponse)
def verify_token(response: Response, current_user=Depends(get_current_user)):
    # Set headers for Nginx auth_request_set to pick up
    response.headers["X-User-Id"] = current_user.id
    response.headers["X-User-Role"] = current_user.role
    response.headers["X-Institution-Id"] = str(current_user.institution_id)
    if current_user.actor_type:
        response.headers["X-Actor-Type"] = current_user.actor_type

    return {
        "user_id": current_user.id,
        "email": current_user.email,
        "role": current_user.role,
        "actor_type": current_user.actor_type,
        "institution_id": current_user.institution_id,
        "full_name": current_user.full_name,
    }
