def test_delete_form_returns_204(admin_client, db_session, create_form):
    form = create_form(institution_id=1)
    response = admin_client.delete(f"/forms/{form.id}")
    assert response.status_code == 204


def test_delete_form_removes_from_db(admin_client, db_session, create_form):
    form = create_form(institution_id=1)
    admin_client.delete(f"/forms/{form.id}")

    response = admin_client.get(f"/forms/{form.id}/status")
    assert response.status_code == 404


def test_delete_form_returns_404_for_nonexistent(admin_client):
    response = admin_client.delete("/forms/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


def test_delete_form_cross_institution_returns_403(
    admin_client, db_session, create_form
):
    form = create_form(institution_id=2)
    response = admin_client.delete(f"/forms/{form.id}")
    assert response.status_code == 403
