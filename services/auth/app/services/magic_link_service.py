import base64
import hashlib
import hmac
import os
import uuid
from dataclasses import dataclass
from typing import Optional
import redis


@dataclass
class MagicLinkConfig:
    """Configuration for magic link token handling."""
    redis_url: str
    secret: str
    ttl_seconds: int


class MagicLinkService:
    def __init__(self, config: MagicLinkConfig, redis_client: Optional[redis.Redis] = None):
        """Create a magic link service backed by Redis."""
        self.config = config
        self.redis = redis_client or redis.Redis.from_url(config.redis_url, decode_responses=True)

    def generate_token(self, email: str) -> str:
        """Generate and store a signed magic link token for an email."""
        token_id = str(uuid.uuid4())
        signature = self._sign(token_id)
        token = f"{token_id}.{signature}"
        self.redis.setex(self._key(token_id), self.config.ttl_seconds, email)
        return token

    def verify_token(self, token: str) -> Optional[str]:
        """Validate a magic link token and return the email if valid."""
        token_id, signature = self._split_token(token)
        if not self._valid_signature(token_id, signature):
            return None
        key = self._key(token_id)
        email = self.redis.get(key)
        if not email:
            return None
        self.redis.delete(key)
        return email

    def _sign(self, token_id: str) -> str:
        """Create a signature for a token id."""
        digest = hmac.new(self.config.secret.encode("utf-8"), token_id.encode("utf-8"), hashlib.sha256).digest()
        return base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")

    def _valid_signature(self, token_id: str, signature: str) -> bool:
        """Verify a token signature."""
        expected = self._sign(token_id)
        return hmac.compare_digest(expected, signature)

    def _split_token(self, token: str):
        """Split a token into id and signature."""
        if "." not in token:
            raise ValueError("Invalid token")
        token_id, signature = token.split(".", 1)
        return token_id, signature

    def _key(self, token_id: str) -> str:
        """Build a Redis key for a token id."""
        return f"magic_link:{token_id}"


def get_magic_link_config() -> MagicLinkConfig:
    """Load magic link configuration from environment."""
    secret = os.getenv("MAGIC_LINK_SECRET")
    if not secret:
        raise RuntimeError("MAGIC_LINK_SECRET is required")
    ttl_seconds = int(os.getenv("MAGIC_LINK_TTL_SECONDS", "900"))
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        raise RuntimeError("REDIS_URL is required")
    return MagicLinkConfig(redis_url=redis_url, secret=secret, ttl_seconds=ttl_seconds)
