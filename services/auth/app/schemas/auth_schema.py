from pydantic import BaseModel, EmailStr


class OAuthCodeRequest(BaseModel):
    code: str
    redirect_uri: str


class MagicLinkRequest(BaseModel):
    email: EmailStr


class MagicLinkVerify(BaseModel):
    token: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenVerifyResponse(BaseModel):
    user_id: str
    email: EmailStr
    role: str
    institution_id: int
