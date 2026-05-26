def test_publish_happy_path_emits_event(
    admin_client, create_workflow, add_step, monkeypatch
):
    workflow = create_workflow()
    add_step(workflow.id, "Start", "admin", 1, False)
    add_step(workflow.id, "End", "staff", 2, True)

    published = {}

    def fake_publish(
        self, workflow_id, institution_id, admin_id, step_count, published_at
    ):
        published["payload"] = {
            "workflow_id": workflow_id,
            "institution_id": institution_id,
            "admin_id": admin_id,
            "step_count": step_count,
            "published_at": published_at,
        }

    monkeypatch.setattr(
        "app.services.event_service.EventService.publish_workflow_published",
        fake_publish,
    )

    response = admin_client.post(f"/workflows/{workflow.id}/publish")
    assert response.status_code == 200
    assert response.json()["status"] == "PUBLISHED"
    assert published["payload"]["step_count"] == 2


def test_publish_no_steps_returns_422(admin_client, create_workflow):
    workflow = create_workflow()
    response = admin_client.post(f"/workflows/{workflow.id}/publish")
    assert response.status_code == 422
    assert "errors" in response.json()["detail"]


def test_publish_no_start_step_returns_422(admin_client, create_workflow, add_step):
    workflow = create_workflow()
    add_step(workflow.id, "Step", "admin", 2, True)
    response = admin_client.post(f"/workflows/{workflow.id}/publish")
    assert response.status_code == 422


def test_publish_missing_terminal_returns_422(admin_client, create_workflow, add_step):
    workflow = create_workflow()
    add_step(workflow.id, "Step", "admin", 1, False)
    response = admin_client.post(f"/workflows/{workflow.id}/publish")
    assert response.status_code == 422


def test_publish_multiple_terminal_returns_422(admin_client, create_workflow, add_step):
    workflow = create_workflow()
    add_step(workflow.id, "A", "admin", 1, True)
    add_step(workflow.id, "B", "staff", 2, True)
    response = admin_client.post(f"/workflows/{workflow.id}/publish")
    assert response.status_code == 422


def test_publish_duplicate_step_order_returns_422(
    admin_client, create_workflow, add_step
):
    workflow = create_workflow()
    add_step(workflow.id, "A", "admin", 1, False)
    add_step(workflow.id, "B", "staff", 1, True)
    response = admin_client.post(f"/workflows/{workflow.id}/publish")
    assert response.status_code == 422


def test_publish_invalid_role_returns_422(admin_client, create_workflow, add_step):
    workflow = create_workflow()
    add_step(workflow.id, "A", "nurse", 1, True)
    response = admin_client.post(f"/workflows/{workflow.id}/publish")
    assert response.status_code == 422


def test_publish_returns_all_errors(admin_client, create_workflow, add_step):
    workflow = create_workflow()
    add_step(workflow.id, "A", "nurse", 2, False)
    response = admin_client.post(f"/workflows/{workflow.id}/publish")
    assert response.status_code == 422
    errors = response.json()["detail"]["errors"]
    assert any("step_order 1" in err for err in errors)
    assert any("terminal" in err for err in errors)
    assert any("Invalid role" in err for err in errors)
