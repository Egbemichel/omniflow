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


def test_by_form_resolves_published_workflow(admin_client):
    created = admin_client.post(
        "/workflows/",
        json={
            "name": "Linked",
            "form_id": "form-abc",
            "steps": [
                {
                    "step_name": "Review",
                    "assigned_role": "staff",
                    "step_order": 1,
                    "is_terminal": True,
                }
            ],
        },
    )
    wf_id = created.json()["id"]
    assert admin_client.post(f"/workflows/{wf_id}/publish").status_code == 200

    resp = admin_client.get("/workflows/by-form/form-abc")
    assert resp.status_code == 200
    assert resp.json()["workflow_id"] == wf_id


def test_by_form_404_when_only_draft(admin_client):
    admin_client.post(
        "/workflows/",
        json={
            "name": "Draft",
            "form_id": "form-draft",
            "steps": [
                {
                    "step_name": "Review",
                    "assigned_role": "staff",
                    "step_order": 1,
                    "is_terminal": True,
                }
            ],
        },
    )
    resp = admin_client.get("/workflows/by-form/form-draft")
    assert resp.status_code == 404


def test_create_persists_graph(admin_client):
    graph = {
        "nodes": [{"id": "n1", "type": "start", "x": 10, "y": 20}],
        "edges": [],
        "formId": "form-123",
    }
    response = admin_client.post(
        "/workflows/",
        json={
            "name": "Graph WF",
            "graph": graph,
            "steps": [
                {
                    "step_name": "Intake",
                    "assigned_role": "end_user",
                    "step_order": 1,
                    "is_terminal": True,
                }
            ],
        },
    )
    assert response.status_code == 201
    assert response.json()["graph"]["formId"] == "form-123"

    wf_id = response.json()["id"]
    detail = admin_client.get(f"/workflows/{wf_id}")
    assert detail.json()["graph"]["nodes"][0]["id"] == "n1"


def test_update_replaces_steps_and_stores_graph(admin_client):
    created = admin_client.post(
        "/workflows/",
        json={
            "name": "Replace WF",
            "steps": [
                {
                    "step_name": "Old",
                    "assigned_role": "staff",
                    "step_order": 1,
                    "is_terminal": True,
                }
            ],
        },
    )
    wf_id = created.json()["id"]
    assert len(created.json()["steps"]) == 1

    updated = admin_client.patch(
        f"/workflows/{wf_id}",
        json={
            "graph": {"nodes": [], "edges": [], "formId": "f2"},
            "steps": [
                {
                    "step_name": "Submit",
                    "assigned_role": "end_user",
                    "step_order": 1,
                    "is_terminal": False,
                },
                {
                    "step_name": "Review",
                    "assigned_role": "staff",
                    "step_order": 2,
                    "is_terminal": True,
                },
            ],
        },
    )
    assert updated.status_code == 200
    body = updated.json()
    assert [s["step_name"] for s in body["steps"]] == ["Submit", "Review"]
    assert body["graph"]["formId"] == "f2"


def test_update_published_does_not_replace_steps(admin_client, create_workflow, add_step):
    workflow = create_workflow(status="PUBLISHED")
    add_step(workflow.id, step_name="Locked", step_order=1)
    response = admin_client.patch(
        f"/workflows/{workflow.id}",
        json={
            "steps": [
                {
                    "step_name": "Hacked",
                    "assigned_role": "staff",
                    "step_order": 1,
                    "is_terminal": True,
                }
            ]
        },
    )
    assert response.status_code == 409
