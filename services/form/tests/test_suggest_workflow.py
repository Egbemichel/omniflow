def test_suggest_workflow_requires_auth(client, create_form):
    form = create_form(institution_id=1)
    response = client.get(f"/forms/{form.id}/suggest-workflow")
    assert response.status_code == 401
