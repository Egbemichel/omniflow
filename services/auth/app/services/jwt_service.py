import os
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt


def _get_jwt_secret() -> str:
    """Read JWT secret from environment."""
    secret = os.getenv("JWT_SECRET")
    if not secret:
        raise RuntimeError("JWT_SECRET is required")
    return secret


def _get_jwt_algorithm() -> str:
    """Read JWT algorithm from environment."""
    return os.getenv("JWT_ALGORITHM", "HS256")


def _get_jwt_expiry_minutes() -> int:
    """Read JWT expiry in minutes from environment."""
    return int(os.getenv("JWT_EXPIRE_MINUTES", "60"))


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a signed JWT for the given payload."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=_get_jwt_expiry_minutes())
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, _get_jwt_secret(), algorithm=_get_jwt_algorithm())


def decode_token(token: str) -> Optional[dict]:
    """Decode a JWT and return the payload if valid."""
    try:
        return jwt.decode(token, _get_jwt_secret(), algorithms=[_get_jwt_algorithm()])
    except JWTError:
        return None
