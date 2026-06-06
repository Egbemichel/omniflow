def test_create_institution_super_admin_only(client):
    response = client.post(
        "/institutions/",
        json={"name": "New Hosp", "type": "hospital"},
        headers={"X-User-Role": "admin"}
    )
    assert response.status_code == 403

def test_create_institution_success(client):
    response = client.post(
        "/institutions/",
        json={"name": "Super Hosp", "type": "hospital"},
        headers={"X-User-Role": "super_admin"}
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Super Hosp"

def test_list_institutions_scoped(client):
    # Non-super admin
    response = client.get("/institutions/", headers={"X-User-Role": "admin", "X-Institution-Id": "1"})
    assert response.status_code == 200
    assert len(response.json()) == 1

def test_get_institution_not_found(client):
    response = client.get("/institutions/9999", headers={"X-User-Role": "super_admin"})
    assert response.status_code == 404

def test_delete_institution_self_error(client):
    response = client.delete(
        "/institutions/1",
        headers={"X-User-Role": "super_admin", "X-Institution-Id": "1"}
    )
    assert response.status_code == 400
