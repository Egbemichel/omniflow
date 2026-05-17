from app.repositories.user_repository import UserRepository
from app.services.jwt_service import decode_token
from app.services.oauth_service import OAuthError


def test_google_login_creates_user_and_returns_token(client, db_session, monkeypatch):
    def fake_exchange(*args, **kwargs):
        return {
            "email": "alice@hospital.com",
            "oauth_id": "google-123",
            "full_name": "Alice Smith",
        }

    monkeypatch.setattr(
        "app.routes.oauth.exchange_google_code",
        fake_exchange,
    )

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
    def fake_exchange(*args, **kwargs):
        raise OAuthError("Login failed")

    monkeypatch.setattr(
        "app.routes.oauth.exchange_google_code",
        fake_exchange,
    )

    response = client.post(
        "/auth/google",
        json={"code": "test", "redirect_uri": "https://app/callback"},
    )
    assert response.status_code == 401


def test_github_login_creates_user_and_returns_token(client, db_session, monkeypatch):
    def fake_exchange(*args, **kwargs):
        return {
            "email": "dev@github.com",
            "oauth_id": "github-999",
            "full_name": "Dev User",
        }

    monkeypatch.setattr(
        "app.routes.oauth.exchange_github_code",
        fake_exchange,
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
