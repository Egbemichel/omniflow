from app.schemas.user_schema import RoleAssign, UserResponse
from app.schemas.auth_schema import (
    MagicLinkRequest,
    MagicLinkVerify,
    OAuthCodeRequest,
    TokenResponse,
    TokenVerifyResponse,
)

__all__ = [
    "RoleAssign",
    "UserResponse",
    "MagicLinkRequest",
    "MagicLinkVerify",
    "OAuthCodeRequest",
    "TokenResponse",
    "TokenVerifyResponse",
]
