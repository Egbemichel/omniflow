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


class TestTaskHealth:
    def test_health_check_returns_200(self, client):
        assert client.get("/health").status_code == 200
