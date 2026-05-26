def test_passkeys_stub_returns_501(client):
    response = client.get("/auth/passkeys")
    assert response.status_code == 501
    assert response.json()["detail"] == "Coming soon"
