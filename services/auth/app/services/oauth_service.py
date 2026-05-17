import logging
from typing import Dict
from authlib.integrations.httpx_client import OAuth2Client

logger = logging.getLogger(__name__)


class OAuthError(Exception):
    """Raised when an OAuth exchange fails."""
    pass


def exchange_google_code(client_id: str, client_secret: str, code: str, redirect_uri: str) -> Dict[str, str]:
    """Exchange a Google OAuth code for user identity."""
    token_url = "https://oauth2.googleapis.com/token"
    userinfo_url = "https://openidconnect.googleapis.com/v1/userinfo"
    try:
        client = OAuth2Client(client_id, client_secret)
        token = client.fetch_token(
            token_url,
            code=code,
            redirect_uri=redirect_uri,
            grant_type="authorization_code",
        )
        resp = client.get(userinfo_url, token=token)
        resp.raise_for_status()
        data = resp.json()
        return {
            "email": data.get("email"),
            "oauth_id": data.get("sub"),
            "full_name": data.get("name"),
        }
    except Exception as exc:
        logger.exception("Google OAuth exchange failed")
        raise OAuthError("Login failed") from exc


def exchange_github_code(client_id: str, client_secret: str, code: str, redirect_uri: str) -> Dict[str, str]:
    """Exchange a GitHub OAuth code for user identity."""
    token_url = "https://github.com/login/oauth/access_token"
    user_url = "https://api.github.com/user"
    emails_url = "https://api.github.com/user/emails"
    try:
        client = OAuth2Client(client_id, client_secret)
        token = client.fetch_token(
            token_url,
            code=code,
            redirect_uri=redirect_uri,
            grant_type="authorization_code",
        )
        user_resp = client.get(user_url, token=token)
        user_resp.raise_for_status()
        user_data = user_resp.json()

        email = user_data.get("email")
        if not email:
            emails_resp = client.get(emails_url, token=token)
            emails_resp.raise_for_status()
            emails = emails_resp.json()
            primary = next((e for e in emails if e.get("primary")), None)
            if primary:
                email = primary.get("email")

        return {
            "email": email,
            "oauth_id": str(user_data.get("id")),
            "full_name": user_data.get("name") or user_data.get("login"),
        }
    except Exception as exc:
        logger.exception("GitHub OAuth exchange failed")
        raise OAuthError("Login failed") from exc
