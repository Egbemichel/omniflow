def test_non_admin_cannot_access_forms(user_client, create_form):
    form = create_form(institution_id=1)
    response = user_client.get(f"/forms/{form.id}/status")
    assert response.status_code == 403
