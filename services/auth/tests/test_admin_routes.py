from app.models.user import User


def test_list_users_as_admin(client, as_user):
    as_user(role="admin", institution_id=1)
    response = client.get("/admin/users")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_list_users_as_super_admin(client, as_user):
    as_user(role="super_admin")
    response = client.get("/admin/users")
    assert response.status_code == 200


def test_assign_role_success(client, db_session, as_user):
    as_user(role="admin", institution_id=1)
    u = User(email="target@x.com", role="end_user", institution_id=1)
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)

    response = client.put(f"/admin/users/{u.id}/role", json={"role": "staff"})
    assert response.status_code == 200
    assert response.json()["role"] == "staff"


def test_update_user_forbidden_for_other_institution(client, db_session, as_user):
    as_user(role="admin", institution_id=1)
    u = User(email="other@x.com", role="end_user", institution_id=2)
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)

    response = client.put(f"/admin/users/{u.id}", json={"full_name": "New Name"})
    assert response.status_code == 404


def test_delete_user_self_error(client, db_session, as_user):
    as_user(role="admin", institution_id=1, user_id="self-id")
    u = User(id="self-id", email="self@x.com", role="admin", institution_id=1)
    db_session.add(u)
    db_session.commit()

    response = client.delete("/admin/users/self-id")
    assert response.status_code == 400
    assert "cannot delete your own account" in response.json()["detail"]


def test_update_user_super_admin_unauthorized(client, db_session, as_user):
    as_user(role="admin", institution_id=1)
    u = User(email="t3@x.com", role="end_user", institution_id=1)
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)

    response = client.put(f"/admin/users/{u.id}", json={"role": "super_admin"})
    assert response.status_code == 403


def test_update_user_success(client, db_session, as_user):
    as_user(role="admin", institution_id=1)
    u = User(email="upd@x.com", role="end_user", institution_id=1)
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)

    response = client.put(
        f"/admin/users/{u.id}",
        json={
            "full_name": "Updated Name",
            "role": "staff",
            "actor_type": "Triage Nurse",
            "is_active": False,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["full_name"] == "Updated Name"
    assert body["role"] == "staff"
    assert body["actor_type"] == "Triage Nurse"
    assert body["is_active"] is False


def test_assign_role_user_not_found(client, as_user):
    as_user(role="admin", institution_id=1)
    response = client.put("/admin/users/does-not-exist/role", json={"role": "staff"})
    assert response.status_code == 404


def test_delete_user_success(client, db_session, as_user):
    as_user(role="admin", institution_id=1)
    u = User(email="gone@x.com", role="staff", institution_id=1)
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)

    response = client.delete(f"/admin/users/{u.id}")
    assert response.status_code == 200
    assert response.json()["status"] == "deleted"
