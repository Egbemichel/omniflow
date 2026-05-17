def test_create_workflow_returns_draft(admin_client):
    response = admin_client.post(
        "/workflows/",
        json={"name": "Patient Intake", "description": "Flow", "form_id": None},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "DRAFT"


def test_non_admin_cannot_create_workflow(staff_client):
    response = staff_client.post(
        "/workflows/",
        json={"name": "Patient Intake", "description": "Flow"},
    )
    assert response.status_code == 403


def test_list_scoped_by_institution(admin_client, create_workflow):
    create_workflow(institution_id=1, name="A")
    create_workflow(institution_id=2, name="B")

    response = admin_client.get("/workflows/")
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["name"] == "A"


def test_get_workflow_cross_institution_forbidden(admin_client, create_workflow):
    workflow = create_workflow(institution_id=2)
    response = admin_client.get(f"/workflows/{workflow.id}")
    assert response.status_code == 403


def test_update_workflow_draft(admin_client, create_workflow):
    workflow = create_workflow()
    response = admin_client.patch(
        f"/workflows/{workflow.id}",
        json={"name": "Updated"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Updated"


def test_update_workflow_published_conflict(admin_client, create_workflow):
    workflow = create_workflow(status="PUBLISHED")
    response = admin_client.patch(
        f"/workflows/{workflow.id}",
        json={"name": "Updated"},
    )
    assert response.status_code == 409


def test_submission_stub_returns_501(admin_client, create_workflow):
    workflow = create_workflow()
    response = admin_client.post(f"/workflows/{workflow.id}/submissions")
    assert response.status_code == 501
