from app.models.user import User


def test_list_users_as_admin(client):
    # Admin is from institution 1 (default from conftest/override_get_db maybe? No, let's create)
    # Actually conftest for auth usually creates a bootstrap admin.
    # Let's check headers.
    response = client.get(
        "/admin/users", headers={"X-User-Role": "admin", "X-Institution-Id": "1"}
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_list_users_as_super_admin(client):
    response = client.get("/admin/users", headers={"X-User-Role": "super_admin"})
    assert response.status_code == 200


def test_assign_role_success(client, db_session):
    u = User(email="target@x.com", role="end_user", institution_id=1)
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)

    response = client.put(
        f"/admin/users/{u.id}/role",
        json={"role": "staff"},
        headers={"X-User-Role": "admin", "X-Institution-Id": "1"},
    )
    assert response.status_code == 200
    assert response.json()["role"] == "staff"


def test_update_user_forbidden_for_other_institution(client, db_session):
    u = User(email="other@x.com", role="end_user", institution_id=2)
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)

    response = client.put(
        f"/admin/users/{u.id}",
        json={"full_name": "New Name"},
        headers={"X-User-Role": "admin", "X-Institution-Id": "1"},
    )
    assert response.status_code == 404


def test_delete_user_self_error(client):
    # If we pass X-User-Id, it should check it.
    # Let's assume the user exists.
    response = client.delete(
        "/admin/users/self-id",
        headers={
            "X-User-Id": "self-id",
            "X-User-Role": "admin",
            "X-Institution-Id": "1",
        },
    )
    assert response.status_code == 400
    assert "cannot delete your own account" in response.json()["detail"]


def test_update_user_super_admin_unauthorized(client, db_session):
    u = User(email="t3@x.com", role="end_user", institution_id=1)
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)

    response = client.put(
        f"/admin/users/{u.id}",
        json={"role": "super_admin"},
        headers={"X-User-Role": "admin", "X-Institution-Id": "1"},
    )
    assert response.status_code == 403
