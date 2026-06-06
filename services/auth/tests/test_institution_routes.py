from app.models.institution import Institution


def test_create_institution_super_admin_only(client, as_user):
    as_user(role="admin", institution_id=1)
    response = client.post(
        "/institutions/", json={"name": "New Hosp", "type": "hospital"}
    )
    assert response.status_code == 403


def test_create_institution_success(client, as_user):
    as_user(role="super_admin")
    response = client.post(
        "/institutions/", json={"name": "Super Hosp", "type": "hospital"}
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Super Hosp"


def test_list_institutions_scoped(client, db_session, as_user):
    inst = Institution(name="Scoped Hosp", type="hospital")
    db_session.add(inst)
    db_session.commit()
    db_session.refresh(inst)

    as_user(role="admin", institution_id=inst.id)
    response = client.get("/institutions/")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == inst.id


def test_get_institution_not_found(client, as_user):
    as_user(role="super_admin")
    response = client.get("/institutions/9999")
    assert response.status_code == 404


def test_delete_institution_self_error(client, as_user):
    as_user(role="super_admin", institution_id=1)
    response = client.delete("/institutions/1")
    assert response.status_code == 400


def test_list_institutions_all_for_super_admin(client, db_session, as_user):
    db_session.add(Institution(name="Hosp A", type="hospital"))
    db_session.add(Institution(name="Hosp B", type="hospital"))
    db_session.commit()

    as_user(role="super_admin")
    response = client.get("/institutions/")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_get_institution_success(client, db_session, as_user):
    inst = Institution(name="Lookup Hosp", type="hospital")
    db_session.add(inst)
    db_session.commit()
    db_session.refresh(inst)

    as_user(role="super_admin")
    response = client.get(f"/institutions/{inst.id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Lookup Hosp"


def test_get_institution_forbidden_for_other_institution(client, db_session, as_user):
    inst = Institution(name="Other Hosp", type="hospital")
    db_session.add(inst)
    db_session.commit()
    db_session.refresh(inst)

    as_user(role="admin", institution_id=inst.id + 1)
    response = client.get(f"/institutions/{inst.id}")
    assert response.status_code == 403


def test_update_institution_success(client, db_session, as_user):
    inst = Institution(name="Old Name", type="hospital")
    db_session.add(inst)
    db_session.commit()
    db_session.refresh(inst)

    as_user(role="super_admin")
    response = client.put(
        f"/institutions/{inst.id}", json={"name": "New Name", "type": "school"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "New Name"
    assert body["type"] == "school"


def test_update_institution_non_super_admin_forbidden(client, as_user):
    as_user(role="admin", institution_id=1)
    response = client.put("/institutions/1", json={"name": "Nope"})
    assert response.status_code == 403


def test_delete_institution_success(client, db_session, as_user):
    inst = Institution(name="Doomed Hosp", type="hospital")
    db_session.add(inst)
    db_session.commit()
    db_session.refresh(inst)

    # Super admin from a different institution can delete this one.
    as_user(role="super_admin", institution_id=inst.id + 1)
    response = client.delete(f"/institutions/{inst.id}")
    assert response.status_code == 200
    assert response.json()["status"] == "deleted"


def test_delete_institution_non_super_admin_forbidden(client, as_user):
    as_user(role="admin", institution_id=1)
    response = client.delete("/institutions/2")
    assert response.status_code == 403
