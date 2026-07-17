import os
import pytest
from datetime import timedelta
from app.services.jwt_service import create_access_token, decode_token, _get_jwt_secret

def test_jwt_encode_decode(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    data = {"sub": "user-123", "role": "admin"}
    token = create_access_token(data)
    decoded = decode_token(token)
    assert decoded["sub"] == "user-123"
    assert decoded["role"] == "admin"
    assert "exp" in decoded

def test_jwt_decode_invalid():
    assert decode_token("invalid-token") is None

def test_jwt_custom_expiry(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    data = {"sub": "user-123"}
    token = create_access_token(data, expires_delta=timedelta(minutes=5))
    decoded = decode_token(token)
    assert decoded["sub"] == "user-123"

def test_get_jwt_secret_missing_error(monkeypatch):
    monkeypatch.delenv("JWT_SECRET", raising=False)
    with pytest.raises(RuntimeError) as exc:
        _get_jwt_secret()
    assert "JWT_SECRET is required" in str(exc.value)
