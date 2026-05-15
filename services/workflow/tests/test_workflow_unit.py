# services/workflow/tests/test_workflow_unit.py


class TestWorkflowCRUD:
    """Tests for creating and managing workflow definitions."""

    def test_create_workflow_returns_201(self, client, admin_headers, sample_workflow_payload):
        response = client.post("/workflows",
            json=sample_workflow_payload,
            headers=admin_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Patient Admission"
        assert data["status"] == "draft"
        assert len(data["steps"]) == 3

    def test_create_workflow_without_steps_returns_422(self, client, admin_headers):
        response = client.post("/workflows",
            json={"name": "Empty Workflow", "steps": []},
            headers=admin_headers
        )
        assert response.status_code == 422

    def test_non_admin_cannot_create_workflow(self, client, nurse_headers, sample_workflow_payload):
        response = client.post("/workflows",
            json=sample_workflow_payload,
            headers=nurse_headers
        )
        assert response.status_code == 403

    def test_publish_draft_workflow_changes_status(self, client, admin_headers, draft_workflow):
        wf_id = draft_workflow["id"]
        response = client.post(f"/workflows/{wf_id}/publish", headers=admin_headers)
        assert response.status_code == 200
        assert response.json()["status"] == "published"

    def test_cannot_publish_already_published_workflow(self, client, admin_headers, published_workflow):
        wf_id = published_workflow["id"]
        response = client.post(f"/workflows/{wf_id}/publish", headers=admin_headers)
        assert response.status_code == 409

    def test_cannot_edit_steps_of_published_workflow(self, client, admin_headers, published_workflow):
        wf_id = published_workflow["id"]
        response = client.post(f"/workflows/{wf_id}/steps",
            json={"order": 4, "name": "New Step", "assigned_role": "nurse"},
            headers=admin_headers
        )
        assert response.status_code == 409

    def test_get_workflow_returns_full_definition(self, client, admin_headers, draft_workflow):
        wf_id = draft_workflow["id"]
        response = client.get(f"/workflows/{wf_id}", headers=admin_headers)
        assert response.status_code == 200
        assert response.json()["id"] == wf_id

    def test_get_nonexistent_workflow_returns_404(self, client, admin_headers):
        response = client.get("/workflows/does-not-exist", headers=admin_headers)
        assert response.status_code == 404


class TestWorkflowStateMachine:
    """Tests for the state machine — the most critical logic."""

    def test_initialise_creates_state_at_step_one(self, client, admin_headers, published_workflow):
        wf_id = published_workflow["id"]
        response = client.post(f"/workflows/{wf_id}/initialise",
            json={"submission_id": "sub-001"},
            headers=admin_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["current_step"] == 1
        assert data["status"] == "in_progress"
        assert data["assigned_role"] == "nurse"

    def test_initialise_on_draft_workflow_returns_409(self, client, admin_headers, draft_workflow):
        wf_id = draft_workflow["id"]
        response = client.post(f"/workflows/{wf_id}/initialise",
            json={"submission_id": "sub-001"},
            headers=admin_headers
        )
        assert response.status_code == 409

    def test_transition_advances_to_next_step(self, client, admin_headers, nurse_headers, published_workflow):
        wf_id = published_workflow["id"]
        client.post(f"/workflows/{wf_id}/initialise",
            json={"submission_id": "sub-001"},
            headers=admin_headers
        )
        response = client.post(f"/workflows/{wf_id}/transition",
            json={"submission_id": "sub-001"},
            headers=nurse_headers   # Step 1 belongs to nurse
        )
        assert response.status_code == 200
        data = response.json()
        assert data["current_step"] == 2
        assert data["assigned_role"] == "doctor"

    def test_wrong_role_cannot_advance_step(self, client, admin_headers, doctor_headers, published_workflow):
        wf_id = published_workflow["id"]
        client.post(f"/workflows/{wf_id}/initialise",
            json={"submission_id": "sub-001"},
            headers=admin_headers
        )
        # Step 1 is nurse — doctor must be rejected
        response = client.post(f"/workflows/{wf_id}/transition",
            json={"submission_id": "sub-001"},
            headers=doctor_headers
        )
        assert response.status_code == 403

    def test_completing_all_steps_marks_submission_completed(self, client, admin_headers, nurse_headers, doctor_headers, published_workflow):
        wf_id = published_workflow["id"]
        # Build admin headers for step 3
        admin_step_headers = {"X-User-Id": "admin-001", "X-User-Role": "admin"}

        client.post(f"/workflows/{wf_id}/initialise",
            json={"submission_id": "sub-001"},
            headers=admin_headers
        )
        client.post(f"/workflows/{wf_id}/transition",
            json={"submission_id": "sub-001"},
            headers=nurse_headers
        )
        client.post(f"/workflows/{wf_id}/transition",
            json={"submission_id": "sub-001"},
            headers=doctor_headers
        )
        response = client.post(f"/workflows/{wf_id}/transition",
            json={"submission_id": "sub-001"},
            headers=admin_step_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["current_step"] is None

    def test_cannot_transition_completed_submission(self, client, admin_headers, nurse_headers, doctor_headers, published_workflow):
        wf_id = published_workflow["id"]
        admin_step_headers = {"X-User-Id": "admin-001", "X-User-Role": "admin"}

        client.post(f"/workflows/{wf_id}/initialise", json={"submission_id": "sub-001"}, headers=admin_headers)
        client.post(f"/workflows/{wf_id}/transition", json={"submission_id": "sub-001"}, headers=nurse_headers)
        client.post(f"/workflows/{wf_id}/transition", json={"submission_id": "sub-001"}, headers=doctor_headers)
        client.post(f"/workflows/{wf_id}/transition", json={"submission_id": "sub-001"}, headers=admin_step_headers)

        # Now try a 4th transition on a completed submission
        response = client.post(f"/workflows/{wf_id}/transition",
            json={"submission_id": "sub-001"},
            headers=admin_step_headers
        )
        assert response.status_code == 409

    def test_transition_unknown_submission_returns_404(self, client, nurse_headers, published_workflow):
        wf_id = published_workflow["id"]
        response = client.post(f"/workflows/{wf_id}/transition",
            json={"submission_id": "does-not-exist"},
            headers=nurse_headers
        )
        assert response.status_code == 404


class TestWorkflowHealth:
    def test_health_check_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"