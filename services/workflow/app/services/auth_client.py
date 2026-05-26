import os
from typing import Dict
import httpx


class AuthClientError(Exception):
    pass


class AuthClient:
    def __init__(self, base_url: str | None = None):
        self.base_url = base_url or os.getenv(
            "AUTH_SERVICE_URL", "http://localhost:8001"
        )

    def verify_token(self, token: str) -> Dict[str, object]:
        url = f"{self.base_url}/auth/verify"
        try:
            response = httpx.get(
                url, headers={"Authorization": f"Bearer {token}"}, timeout=5
            )
        except httpx.RequestError as exc:
            raise AuthClientError("Auth service unreachable") from exc

        if response.status_code != 200:
            raise AuthClientError("Invalid token")
        return response.json()
