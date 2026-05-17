import os
from dataclasses import dataclass


@dataclass(frozen=True)
class OAuthSettings:
    """OAuth and magic link configuration."""
    google_client_id: str
    google_client_secret: str
    github_client_id: str
    github_client_secret: str
    magic_link_secret: str
    magic_link_ttl_seconds: int
    redis_url: str
    google_enabled: bool
    github_enabled: bool
    magic_link_enabled: bool


def _get_bool(name: str, default: bool) -> bool:
    """Parse boolean environment variables."""
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def get_oauth_settings() -> OAuthSettings:
    """Load OAuth and magic link settings from environment."""
    google_client_id = os.getenv("GOOGLE_CLIENT_ID", "")
    google_client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")
    github_client_id = os.getenv("GITHUB_CLIENT_ID", "")
    github_client_secret = os.getenv("GITHUB_CLIENT_SECRET", "")
    magic_link_secret = os.getenv("MAGIC_LINK_SECRET", "")
    redis_url = os.getenv("REDIS_URL", "")
    magic_link_ttl_seconds = int(os.getenv("MAGIC_LINK_TTL_SECONDS", "900"))

    google_enabled = _get_bool(
        "GOOGLE_OAUTH_ENABLED", bool(google_client_id and google_client_secret)
    )
    github_enabled = _get_bool(
        "GITHUB_OAUTH_ENABLED", bool(github_client_id and github_client_secret)
    )
    magic_link_enabled = _get_bool("MAGIC_LINK_ENABLED", bool(magic_link_secret))

    if google_enabled and (not google_client_id or not google_client_secret):
        raise RuntimeError("Google OAuth is enabled but missing credentials")
    if github_enabled and (not github_client_id or not github_client_secret):
        raise RuntimeError("GitHub OAuth is enabled but missing credentials")
    if magic_link_enabled and (not magic_link_secret or not redis_url):
        raise RuntimeError("Magic link is enabled but missing config")

    return OAuthSettings(
        google_client_id=google_client_id,
        google_client_secret=google_client_secret,
        github_client_id=github_client_id,
        github_client_secret=github_client_secret,
        magic_link_secret=magic_link_secret,
        magic_link_ttl_seconds=magic_link_ttl_seconds,
        redis_url=redis_url,
        google_enabled=google_enabled,
        github_enabled=github_enabled,
        magic_link_enabled=magic_link_enabled,
    )
