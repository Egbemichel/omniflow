# services/task/tests/test_task_unit.py


class TestSubmissions:
    def test_create_submission_returns_201(
        self, client, end_user_headers, mock_workflow_service
    ):
        response = client.post(
            "/submissions",
            json={"workflow_id": "wf-001", "form_data": {"field_1": "value_1"}},
            headers=end_user_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["status"] == "in_progress"

    def test_submission_creates_task_for_step_one(
        self, client, end_user_headers, mock_workflow_service
    ):
        response = client.post(
            "/submissions",
            json={"workflow_id": "wf-001", "form_data": {"field_1": "value_1"}},
            headers=end_user_headers,
        )
        submission_id = response.json()["id"]

        # The task should now exist
        tasks = client.get(
            "/tasks/inbox", headers={"X-User-Id": "nurse-001", "X-User-Role": "nurse"}
        )
        task_ids = [t["submission_id"] for t in tasks.json()]
        assert submission_id in task_ids

    def test_create_submission_missing_workflow_id_returns_422(
        self, client, end_user_headers
    ):
        response = client.post(
            "/submissions",
            json={"form_data": {"field": "val"}},
            headers=end_user_headers,
        )
        assert response.status_code == 422

    def test_get_submission_status(self, client, end_user_headers, created_submission):
        sub_id = created_submission["id"]
        response = client.get(f"/submissions/{sub_id}/status", headers=end_user_headers)
        assert response.status_code == 200
        assert response.json()["status"] == "in_progress"

    def test_user_cannot_view_other_users_submissions(self, client, created_submission):
        sub_id = created_submission["id"]
        other_user_headers = {"X-User-Id": "other-999", "X-User-Role": "end_user"}
        response = client.get(
            f"/submissions/{sub_id}/status", headers=other_user_headers
        )
        assert response.status_code == 403

    def test_get_history_nonexistent_submission_returns_404(
        self, client, nurse_headers
    ):
        response = client.get("/submissions/missing/history", headers=nurse_headers)
        assert response.status_code == 404


class TestTaskInbox:
    def test_staff_sees_tasks_assigned_to_their_role(
        self, client, nurse_headers, created_submission
    ):
        response = client.get("/tasks/inbox", headers=nurse_headers)
        assert response.status_code == 200
        tasks = response.json()
        assert len(tasks) == 1
        assert tasks[0]["assigned_role"] == "nurse"

    def test_doctor_does_not_see_nurse_tasks(
        self, client, doctor_headers, created_submission
    ):
        response = client.get("/tasks/inbox", headers=doctor_headers)
        assert response.status_code == 200
        assert len(response.json()) == 0

    def test_unauthenticated_inbox_returns_401(self, client):
        response = client.get("/tasks/inbox")
        assert response.status_code == 401


class TestTaskCompletion:
    def test_complete_task_advances_workflow(
        self, client, nurse_headers, created_submission, mock_workflow_service
    ):
        tasks = client.get("/tasks/inbox", headers=nurse_headers)
        task_id = tasks.json()[0]["id"]

        response = client.post(f"/tasks/{task_id}/complete", headers=nurse_headers)
        assert response.status_code == 200
        mock_workflow_service["advance"].assert_called_once()

    def test_complete_task_appends_audit_history(
        self, client, nurse_headers, created_submission, mock_workflow_service
    ):
        tasks = client.get("/tasks/inbox", headers=nurse_headers)
        task_id = tasks.json()[0]["id"]
        sub_id = created_submission["id"]

        client.post(f"/tasks/{task_id}/complete", headers=nurse_headers)

        history = client.get(f"/submissions/{sub_id}/history", headers=nurse_headers)
        assert history.status_code == 200
        events = history.json()
        assert len(events) >= 1
        assert events[0]["action"] == "task_completed"
        assert events[0]["actor_id"] == "nurse-001"

    def test_wrong_role_cannot_complete_task(
        self, client, doctor_headers, created_submission
    ):
        """Step 1 is assigned to nurse — doctor must not complete it."""
        nurse_tasks = client.get(
            "/tasks/inbox", headers={"X-User-Id": "nurse-001", "X-User-Role": "nurse"}
        )
        task_id = nurse_tasks.json()[0]["id"]

        response = client.post(f"/tasks/{task_id}/complete", headers=doctor_headers)
        assert response.status_code == 403

    def test_cannot_complete_already_completed_task(
        self, client, nurse_headers, created_submission, mock_workflow_service
    ):
        tasks = client.get("/tasks/inbox", headers=nurse_headers)
        task_id = tasks.json()[0]["id"]

        client.post(f"/tasks/{task_id}/complete", headers=nurse_headers)
        response = client.post(f"/tasks/{task_id}/complete", headers=nurse_headers)
        assert response.status_code == 409

    def test_complete_nonexistent_task_returns_404(self, client, nurse_headers):
        response = client.post("/tasks/does-not-exist/complete", headers=nurse_headers)
        assert response.status_code == 404


class TestFormIdResolution:
    """Public form submissions arrive with a form_id; the workflow is resolved."""

    def test_form_id_resolves_published_workflow(self, client, end_user_headers):
        from unittest.mock import patch

        with (
            patch("app.services.workflow_client.find_workflow_for_form") as mfind,
            patch("app.services.workflow_client.initialise_submission") as minit,
        ):
            mfind.return_value = "wf-resolved"
            minit.return_value = {
                "next_step_id": "n1",
                "assigned_role": "staff",
                "actor_type": None,
                "status": "IN_PROGRESS",
            }
            resp = client.post(
                "/submissions",
                json={"form_id": "form-1", "form_data": {"a": "b"}},
                headers=end_user_headers,
            )
        assert resp.status_code == 201
        mfind.assert_called_once_with("form-1")
        assert resp.json()["workflow_id"] == "wf-resolved"

    def test_form_id_without_published_workflow_returns_422(
        self, client, end_user_headers
    ):
        from unittest.mock import patch

        with patch("app.services.workflow_client.find_workflow_for_form") as mfind:
            mfind.return_value = None
            resp = client.post(
                "/submissions",
                json={"form_id": "no-workflow", "form_data": {}},
                headers=end_user_headers,
            )
        assert resp.status_code == 422


class TestActorTypeRouting:
    """Graph-driven workflows route tasks by actor type, not the broad role."""

    def _submit_with_actor_type(self, client, end_user_headers, actor_type):
        from unittest.mock import patch

        with patch("app.services.workflow_client.initialise_submission") as m:
            m.return_value = {
                "next_step_id": "node-1",
                "assigned_role": "staff",
                "actor_type": actor_type,
                "status": "IN_PROGRESS",
            }
            resp = client.post(
                "/submissions",
                json={"workflow_id": "wf-graph", "form_data": {}},
                headers=end_user_headers,
            )
        assert resp.status_code == 201
        return resp.json()

    def test_matching_actor_type_sees_task(self, client, end_user_headers):
        self._submit_with_actor_type(client, end_user_headers, "Triage Nurse")
        inbox = client.get(
            "/tasks/inbox",
            headers={
                "X-User-Id": "s1",
                "X-User-Role": "staff",
                "X-Actor-Type": "Triage Nurse",
            },
        )
        body = inbox.json()
        assert len(body) == 1
        assert body[0]["actor_type"] == "Triage Nurse"

    def test_other_actor_type_does_not_see_task(self, client, end_user_headers):
        self._submit_with_actor_type(client, end_user_headers, "Triage Nurse")
        inbox = client.get(
            "/tasks/inbox",
            headers={
                "X-User-Id": "s2",
                "X-User-Role": "staff",
                "X-Actor-Type": "Blood Lab",
            },
        )
        assert inbox.json() == []


class TestTaskHealth:
    def test_health_check_returns_200(self, client):
        assert client.get("/health").status_code == 200
