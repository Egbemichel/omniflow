def test_add_step_draft(admin_client, create_workflow):
    workflow = create_workflow()
    response = admin_client.post(
        f"/workflows/{workflow.id}/steps",
        json={
            "step_name": "Review",
            "assigned_role": "staff",
            "step_order": 1,
            "is_terminal": True,
        },
    )
    assert response.status_code == 201


def test_add_step_invalid_role_returns_422(admin_client, create_workflow):
    workflow = create_workflow()
    response = admin_client.post(
        f"/workflows/{workflow.id}/steps",
        json={
            "step_name": "Review",
            "assigned_role": "nurse",
            "step_order": 1,
            "is_terminal": True,
        },
    )
    assert response.status_code == 422


def test_update_step_draft(admin_client, create_workflow, add_step):
    workflow = create_workflow()
    step = add_step(workflow.id, "Review", "staff", 1, False)

    response = admin_client.patch(
        f"/workflows/{workflow.id}/steps/{step.id}",
        json={"step_name": "Updated", "assigned_role": "admin"},
    )
    assert response.status_code == 200
    assert response.json()["step_name"] == "Updated"


def test_delete_step_draft(admin_client, create_workflow, add_step):
    workflow = create_workflow()
    step = add_step(workflow.id, "Review", "staff", 1, False)

    response = admin_client.delete(f"/workflows/{workflow.id}/steps/{step.id}")
    assert response.status_code == 200


def test_edit_step_after_publish_conflict(admin_client, create_workflow, add_step):
    workflow = create_workflow()
    step = add_step(workflow.id, "Review", "staff", 1, True)
    admin_client.post(f"/workflows/{workflow.id}/publish")

    response = admin_client.patch(
        f"/workflows/{workflow.id}/steps/{step.id}",
        json={"step_name": "Updated"},
    )
    assert response.status_code == 409
