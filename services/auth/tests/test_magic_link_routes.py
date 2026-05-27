from unittest.mock import MagicMock, patch
from app.repositories.user_repository import UserRepository


def test_magic_link_request_and_verify_flow(
    client_with_magic_link_override, db_session
):
    with patch("app.routes.magic_link.send_magic_link"):
        response = client_with_magic_link_override.post(
            "/auth/magic-link/request",
            json={"email": "magic@pk.com"},
        )
    assert response.status_code == 200
    assert "sign-in link" in response.json()["message"]

    svc = client_with_magic_link_override.app.dependency_overrides[
        __import__(
            "app.routes.magic_link", fromlist=["get_magic_link_service"]
        ).get_magic_link_service
    ]()
    token = svc.generate_token("magic@pk.com")

    verify = client_with_magic_link_override.get(
        f"/auth/magic-link/verify?token={token}",
        follow_redirects=False,
    )
    assert verify.status_code in (302, 307)
    assert "oauth-success.html" in verify.headers["location"]

    repo = UserRepository(db_session)
    user = repo.get_by_email("magic@pk.com")
    assert user is not None
    assert user.oauth_provider == "magic_link"


def test_magic_link_single_use_token(
    client_with_magic_link_override, magic_link_service
):
    token = magic_link_service.generate_token("once@pk.com")

    first = client_with_magic_link_override.get(
        f"/auth/magic-link/verify?token={token}",
        follow_redirects=False,
    )
    assert first.status_code in (302, 307)
    assert "oauth-success.html" in first.headers["location"]

    second = client_with_magic_link_override.get(
        f"/auth/magic-link/verify?token={token}",
        follow_redirects=False,
    )
    assert second.status_code in (302, 307)
    assert "invalid_link" in second.headers["location"]


def test_magic_link_invalid_token_returns_401(client_with_magic_link_override):
    response = client_with_magic_link_override.get(
        "/auth/magic-link/verify?token=bad.token",
        follow_redirects=False,
    )
    assert response.status_code in (302, 307)
    assert "invalid_link" in response.headers["location"]


def test_magic_link_request_disabled(client, monkeypatch):
    from app.routes.magic_link import get_magic_link_service

    def raise_runtime():
        raise RuntimeError("not configured")

    client.app.dependency_overrides[get_magic_link_service] = raise_runtime
    try:
        response = client.post(
            "/auth/magic-link/request",
            json={"email": "test@pk.com"},
        )
        assert response.status_code == 503
    finally:
        client.app.dependency_overrides.pop(get_magic_link_service, None)


def test_magic_link_request_sends_email(client_with_magic_link_override, monkeypatch):
    sent = []
    monkeypatch.setattr(
        "app.routes.magic_link.send_magic_link",
        lambda email, link: sent.append((email, link)),
    )
    response = client_with_magic_link_override.post(
        "/auth/magic-link/request",
        json={"email": "send@pk.com"},
    )
    assert response.status_code == 200
    assert len(sent) == 1
    assert sent[0][0] == "send@pk.com"
    assert "magic-link/verify" in sent[0][1]


def test_magic_link_verify_inactive_user(
    client_with_magic_link_override, magic_link_service
):
    token = magic_link_service.generate_token("inactive@pk.com")
    inactive = MagicMock()
    inactive.is_active = False

    with patch(
        "app.routes.magic_link.UserRepository.get_by_email",
        return_value=inactive,
    ):
        response = client_with_magic_link_override.get(
            f"/auth/magic-link/verify?token={token}",
            follow_redirects=False,
        )
    assert response.status_code in (302, 307)
    assert "inactive" in response.headers["location"]
