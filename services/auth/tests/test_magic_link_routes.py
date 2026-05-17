from app.repositories.user_repository import UserRepository
from app.services.jwt_service import decode_token


def test_magic_link_request_and_verify_flow(
    client_with_magic_link_override, db_session
):
    request = client_with_magic_link_override.post(
        "/auth/magic-link/request",
        json={"email": "magic@pk.com"},
    )
    assert request.status_code == 200
    token = request.json()["token"]

    verify = client_with_magic_link_override.post(
        "/auth/magic-link/verify",
        json={"token": token},
    )
    assert verify.status_code == 200
    payload = decode_token(verify.json()["access_token"])
    assert payload["email"] == "magic@pk.com"

    repo = UserRepository(db_session)
    user = repo.get_by_email("magic@pk.com")
    assert user is not None
    assert user.oauth_provider == "magic_link"
    assert user.oauth_id == "magic@pk.com"


def test_magic_link_single_use_token(client_with_magic_link_override):
    request = client_with_magic_link_override.post(
        "/auth/magic-link/request",
        json={"email": "once@pk.com"},
    )
    token = request.json()["token"]

    first = client_with_magic_link_override.post(
        "/auth/magic-link/verify",
        json={"token": token},
    )
    assert first.status_code == 200

    second = client_with_magic_link_override.post(
        "/auth/magic-link/verify",
        json={"token": token},
    )
    assert second.status_code == 401


def test_magic_link_invalid_token_returns_401(client_with_magic_link_override):
    response = client_with_magic_link_override.post(
        "/auth/magic-link/verify",
        json={"token": "bad"},
    )
    assert response.status_code == 401
