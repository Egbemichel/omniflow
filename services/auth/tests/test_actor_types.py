from app.services.jwt_service import create_access_token, decode_token


def _auth_header(user):
    token = create_access_token(
        {
            "sub": user.id,
            "email": user.email,
            "role": user.role,
            "institution_id": user.institution_id,
        }
    )
    return {"Authorization": f"Bearer {token}"}


def test_create_actor_type_with_any_role(client, db_session, create_user):
    admin = create_user(db_session, email="admin@h.com", role="admin", institution_id=5)
    resp = client.post(
        "/admin/actor-types",
        headers=_auth_header(admin),
        json={"label": "Registrar", "system_role": "admin"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["label"] == "Registrar"
    assert body["system_role"] == "admin"


def test_create_actor_type_defaults_to_staff(client, db_session, create_user):
    admin = create_user(db_session, email="a2@h.com", role="admin", institution_id=5)
    resp = client.post(
        "/admin/actor-types",
        headers=_auth_header(admin),
        json={"label": "Triage Nurse"},
    )
    assert resp.status_code == 201
    assert resp.json()["system_role"] == "staff"


def test_list_is_institution_scoped_and_deletable(client, db_session, create_user):
    admin = create_user(db_session, email="a3@h.com", role="admin", institution_id=7)
    client.post(
        "/admin/actor-types",
        headers=_auth_header(admin),
        json={"label": "Blood Lab", "system_role": "staff"},
    )
    listed = client.get("/admin/actor-types", headers=_auth_header(admin))
    assert listed.status_code == 200
    items = listed.json()
    assert len(items) == 1

    at_id = items[0]["id"]
    deleted = client.delete(f"/admin/actor-types/{at_id}", headers=_auth_header(admin))
    assert deleted.status_code == 204
    assert client.get("/admin/actor-types", headers=_auth_header(admin)).json() == []


def test_duplicate_label_rejected(client, db_session, create_user):
    admin = create_user(db_session, email="a4@h.com", role="admin", institution_id=9)
    client.post(
        "/admin/actor-types", headers=_auth_header(admin), json={"label": "Nurse"}
    )
    dup = client.post(
        "/admin/actor-types", headers=_auth_header(admin), json={"label": "Nurse"}
    )
    assert dup.status_code == 409


def test_invalid_role_rejected(client, db_session, create_user):
    admin = create_user(db_session, email="a5@h.com", role="admin", institution_id=11)
    resp = client.post(
        "/admin/actor-types",
        headers=_auth_header(admin),
        json={"label": "X", "system_role": "wizard"},
    )
    assert resp.status_code == 422


def test_registered_actor_type_sets_role_on_login(
    client, db_session, create_user, monkeypatch
):
    """A registered actor type mapped to a non-staff role applies on CSV login."""
    admin = create_user(
        db_session, email="admin42@h.com", role="institution_admin", institution_id=42
    )
    client.post(
        "/admin/actor-types",
        headers=_auth_header(admin),
        json={"label": "Registrar", "system_role": "admin"},
    )
    csv_content = "name,email,role,department\nRita Reg,rita@h.com,Registrar,Office\n"
    upload = client.post(
        "/admin/institutions/42/staff/upload",
        headers=_auth_header(admin),
        files={"file": ("staff.csv", csv_content, "text/csv")},
    )
    assert upload.status_code == 200

    monkeypatch.setattr(
        "app.routes.oauth.exchange_google_code",
        lambda *a, **kw: {
            "email": "rita@h.com",
            "oauth_id": "g-rita",
            "full_name": "Rita",
        },
    )
    resp = client.post(
        "/auth/google", json={"code": "t", "redirect_uri": "https://app/cb"}
    )
    assert resp.status_code == 200
    payload = decode_token(resp.json()["access_token"])
    assert payload["role"] == "admin"
    assert payload["actor_type"] == "Registrar"
