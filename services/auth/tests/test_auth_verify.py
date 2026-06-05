from app.services.jwt_service import create_access_token


def test_verify_valid_token_returns_user_info(client, db_session, create_user):
    user = create_user(db_session, email="verify@pk.com", full_name="Verify User")
    token = create_access_token(
        {
            "sub": user.id,
            "email": user.email,
            "role": user.role,
            "institution_id": user.institution_id,
        }
    )
    response = client.get("/auth/verify", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == user.id
    assert data["email"] == user.email
    assert data["role"] == user.role
    assert data["institution_id"] == user.institution_id
    assert data["full_name"] == "Verify User"


def test_verify_invalid_token_returns_401(client):
    response = client.get(
        "/auth/verify", headers={"Authorization": "Bearer invalid.token.here"}
    )
    assert response.status_code == 401


def test_admin_user_list_is_scoped_by_institution(client, db_session, create_user):
    admin = create_user(
        db_session, email="admin@pk.com", role="admin", institution_id=1
    )
    create_user(db_session, email="staff@pk.com", role="staff", institution_id=1)
    create_user(db_session, email="other@pk.com", role="staff", institution_id=2)

    token = create_access_token(
        {
            "sub": admin.id,
            "email": admin.email,
            "role": admin.role,
            "institution_id": admin.institution_id,
        }
    )

    response = client.get("/admin/users", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    emails = {user["email"] for user in response.json()}
    assert "admin@pk.com" in emails
    assert "staff@pk.com" in emails
    assert "other@pk.com" not in emails


def test_admin_assign_role_only_within_institution(client, db_session, create_user):
    admin = create_user(
        db_session, email="admin@pk.com", role="admin", institution_id=1
    )
    target = create_user(
        db_session, email="target@pk.com", role="end_user", institution_id=1
    )
    outsider = create_user(
        db_session, email="out@pk.com", role="end_user", institution_id=2
    )

    token = create_access_token(
        {
            "sub": admin.id,
            "email": admin.email,
            "role": admin.role,
            "institution_id": admin.institution_id,
        }
    )

    ok = client.put(
        f"/admin/users/{target.id}/role",
        json={"role": "staff"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert ok.status_code == 200
    assert ok.json()["role"] == "staff"

    bad = client.put(
        f"/admin/users/{outsider.id}/role",
        json={"role": "staff"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert bad.status_code == 404
