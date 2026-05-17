import pytest
from unittest.mock import MagicMock, patch

from app.repositories.user_repository import UserRepository
from app.services.jwt_service import decode_token
from app.services.oauth_service import (
    OAuthError,
    exchange_google_code,
    exchange_github_code,
)


# ---------------------------------------------------------------------------
# Google route tests
# ---------------------------------------------------------------------------


def test_google_login_creates_user_and_returns_token(client, db_session, monkeypatch):
    def fake_exchange(*args, **kwargs):
        return {
            "email": "alice@hospital.com",
            "oauth_id": "google-123",
            "full_name": "Alice Smith",
        }

    monkeypatch.setattr("app.routes.oauth.exchange_google_code", fake_exchange)

    response = client.post(
        "/auth/google",
        json={"code": "test", "redirect_uri": "https://app/callback"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    payload = decode_token(token)
    assert payload["email"] == "alice@hospital.com"
    assert payload["role"] == "end_user"
    assert payload["institution_id"] == 1

    repo = UserRepository(db_session)
    user = repo.get_by_email("alice@hospital.com")
    assert user is not None
    assert user.oauth_provider == "google"
    assert user.oauth_id == "google-123"


def test_google_login_missing_fields_returns_422(client):
    response = client.post("/auth/google", json={})
    assert response.status_code == 422


def test_google_login_exchange_error_returns_401(client, monkeypatch):
    monkeypatch.setattr(
        "app.routes.oauth.exchange_google_code",
        lambda *a, **kw: (_ for _ in ()).throw(OAuthError("Login failed")),
    )
    response = client.post(
        "/auth/google",
        json={"code": "test", "redirect_uri": "https://app/callback"},
    )
    assert response.status_code == 401


def test_google_login_missing_email_returns_401(client, monkeypatch):
    """exchange returns a dict with no email — route must return 401."""
    monkeypatch.setattr(
        "app.routes.oauth.exchange_google_code",
        lambda *a, **kw: {"email": None, "oauth_id": "google-123", "full_name": "X"},
    )
    response = client.post(
        "/auth/google",
        json={"code": "test", "redirect_uri": "https://app/callback"},
    )
    assert response.status_code == 401


def test_google_login_missing_oauth_id_returns_401(client, monkeypatch):
    """exchange returns a dict with no oauth_id — route must return 401."""
    monkeypatch.setattr(
        "app.routes.oauth.exchange_google_code",
        lambda *a, **kw: {"email": "x@x.com", "oauth_id": None, "full_name": "X"},
    )
    response = client.post(
        "/auth/google",
        json={"code": "test", "redirect_uri": "https://app/callback"},
    )
    assert response.status_code == 401


def test_google_login_inactive_user_returns_403(client, db_session, monkeypatch):
    """User exists but is inactive — route must return 403."""
    monkeypatch.setattr(
        "app.routes.oauth.exchange_google_code",
        lambda *a, **kw: {
            "email": "inactive@hospital.com",
            "oauth_id": "google-inactive",
            "full_name": "Inactive",
        },
    )

    # Patch upsert to return an inactive user
    inactive = MagicMock()
    inactive.is_active = False

    monkeypatch.setattr(
        "app.routes.oauth.UserRepository.upsert_oauth_user",
        lambda *a, **kw: (inactive, False),
    )

    response = client.post(
        "/auth/google",
        json={"code": "test", "redirect_uri": "https://app/callback"},
    )
    assert response.status_code == 403


def test_google_login_disabled_returns_503(client, monkeypatch):
    """When google_enabled=False the route returns 503."""
    mock_settings = MagicMock()
    mock_settings.google_enabled = False
    monkeypatch.setattr("app.routes.oauth.get_oauth_settings", lambda: mock_settings)

    response = client.post(
        "/auth/google",
        json={"code": "test", "redirect_uri": "https://app/callback"},
    )
    assert response.status_code == 503


def test_google_login_settings_runtime_error_returns_503(client, monkeypatch):
    """When get_oauth_settings raises RuntimeError the route returns 503."""
    monkeypatch.setattr(
        "app.routes.oauth.get_oauth_settings",
        lambda: (_ for _ in ()).throw(RuntimeError("missing env")),
    )
    response = client.post(
        "/auth/google",
        json={"code": "test", "redirect_uri": "https://app/callback"},
    )
    assert response.status_code == 503


# ---------------------------------------------------------------------------
# GitHub route tests
# ---------------------------------------------------------------------------


def test_github_login_creates_user_and_returns_token(client, db_session, monkeypatch):
    monkeypatch.setattr(
        "app.routes.oauth.exchange_github_code",
        lambda *a, **kw: {
            "email": "dev@github.com",
            "oauth_id": "github-999",
            "full_name": "Dev User",
        },
    )

    response = client.post(
        "/auth/github",
        json={"code": "test", "redirect_uri": "https://app/callback"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    payload = decode_token(token)
    assert payload["email"] == "dev@github.com"
    assert payload["role"] == "end_user"

    repo = UserRepository(db_session)
    user = repo.get_by_email("dev@github.com")
    assert user is not None
    assert user.oauth_provider == "github"
    assert user.oauth_id == "github-999"


def test_github_login_exchange_error_returns_401(client, monkeypatch):
    monkeypatch.setattr(
        "app.routes.oauth.exchange_github_code",
        lambda *a, **kw: (_ for _ in ()).throw(OAuthError("Login failed")),
    )
    response = client.post(
        "/auth/github",
        json={"code": "test", "redirect_uri": "https://app/callback"},
    )
    assert response.status_code == 401


def test_github_login_missing_email_returns_401(client, monkeypatch):
    monkeypatch.setattr(
        "app.routes.oauth.exchange_github_code",
        lambda *a, **kw: {"email": None, "oauth_id": "github-999", "full_name": "X"},
    )
    response = client.post(
        "/auth/github",
        json={"code": "test", "redirect_uri": "https://app/callback"},
    )
    assert response.status_code == 401


def test_github_login_disabled_returns_503(client, monkeypatch):
    mock_settings = MagicMock()
    mock_settings.github_enabled = False
    monkeypatch.setattr("app.routes.oauth.get_oauth_settings", lambda: mock_settings)

    response = client.post(
        "/auth/github",
        json={"code": "test", "redirect_uri": "https://app/callback"},
    )
    assert response.status_code == 503


def test_github_login_inactive_user_returns_403(client, monkeypatch):
    monkeypatch.setattr(
        "app.routes.oauth.exchange_github_code",
        lambda *a, **kw: {
            "email": "inactive@gh.com",
            "oauth_id": "github-inactive",
            "full_name": "Inactive",
        },
    )
    inactive = MagicMock()
    inactive.is_active = False
    monkeypatch.setattr(
        "app.routes.oauth.UserRepository.upsert_oauth_user",
        lambda *a, **kw: (inactive, False),
    )
    response = client.post(
        "/auth/github",
        json={"code": "test", "redirect_uri": "https://app/callback"},
    )
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# oauth_service unit tests (covers the 20% gap directly)
# ---------------------------------------------------------------------------


def test_exchange_google_code_raises_oauth_error_on_failure():
    """exchange_google_code wraps any exception in OAuthError."""
    with patch("app.services.oauth_service.OAuth2Client") as MockClient:
        MockClient.return_value.fetch_token.side_effect = Exception("network error")
        with pytest.raises(OAuthError):
            exchange_google_code("id", "secret", "code", "https://redirect")


def test_exchange_google_code_returns_user_info():
    """exchange_google_code maps Google userinfo fields correctly."""
    mock_token = {"access_token": "tok"}
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "email": "user@gmail.com",
        "sub": "google-sub-123",
        "name": "Google User",
    }
    mock_resp.raise_for_status = MagicMock()

    with patch("app.services.oauth_service.OAuth2Client") as MockClient:
        instance = MockClient.return_value
        instance.fetch_token.return_value = mock_token
        instance.get.return_value = mock_resp

        result = exchange_google_code("id", "secret", "code", "https://redirect")

    assert result["email"] == "user@gmail.com"
    assert result["oauth_id"] == "google-sub-123"
    assert result["full_name"] == "Google User"


def test_exchange_github_code_raises_oauth_error_on_failure():
    """exchange_github_code wraps any exception in OAuthError."""
    with patch("app.services.oauth_service.OAuth2Client") as MockClient:
        MockClient.return_value.fetch_token.side_effect = Exception("network error")
        with pytest.raises(OAuthError):
            exchange_github_code("id", "secret", "code", "https://redirect")


def test_exchange_github_code_returns_user_info():
    """exchange_github_code maps GitHub user fields correctly."""
    mock_token = {"access_token": "tok"}
    mock_user_resp = MagicMock()
    mock_user_resp.json.return_value = {
        "email": "dev@github.com",
        "id": 999,
        "name": "Dev User",
        "login": "devuser",
    }
    mock_user_resp.raise_for_status = MagicMock()

    with patch("app.services.oauth_service.OAuth2Client") as MockClient:
        instance = MockClient.return_value
        instance.fetch_token.return_value = mock_token
        instance.get.return_value = mock_user_resp

        result = exchange_github_code("id", "secret", "code", "https://redirect")

    assert result["email"] == "dev@github.com"
    assert result["oauth_id"] == "999"
    assert result["full_name"] == "Dev User"


def test_exchange_github_code_fetches_email_from_emails_endpoint():
    """When user.email is None, falls back to /user/emails endpoint."""
    mock_token = {"access_token": "tok"}

    mock_user_resp = MagicMock()
    mock_user_resp.json.return_value = {
        "email": None,
        "id": 888,
        "name": None,
        "login": "nomail",
    }
    mock_user_resp.raise_for_status = MagicMock()

    mock_emails_resp = MagicMock()
    mock_emails_resp.json.return_value = [
        {"email": "primary@gh.com", "primary": True},
        {"email": "other@gh.com", "primary": False},
    ]
    mock_emails_resp.raise_for_status = MagicMock()

    with patch("app.services.oauth_service.OAuth2Client") as MockClient:
        instance = MockClient.return_value
        instance.fetch_token.return_value = mock_token
        instance.get.side_effect = [mock_user_resp, mock_emails_resp]

        result = exchange_github_code("id", "secret", "code", "https://redirect")

    assert result["email"] == "primary@gh.com"
    assert result["full_name"] == "nomail"  # falls back to login
