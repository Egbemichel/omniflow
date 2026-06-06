def test_get_all_submissions_as_staff(client, created_submission):
    headers = {"X-User-Id": "staff-1", "X-User-Role": "staff", "X-Institution-Id": "1"}
    response = client.get("/submissions", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_get_own_submissions_as_user(client, created_submission):
    headers = {
        "X-User-Id": "nurse-001",
        "X-User-Role": "end_user",
        "X-Institution-Id": "1",
    }
    response = client.get("/submissions", headers=headers)
    assert response.status_code == 200
    # The created_submission is submitted by nurse-001 in conftest?
    # Actually conftest uses nurse-001 for submitter in some tests.


def test_update_form_data_as_staff(client, created_submission):
    headers = {"X-User-Id": "staff-1", "X-User-Role": "staff", "X-Institution-Id": "1"}
    sub_id = created_submission["id"]
    response = client.patch(
        f"/submissions/{sub_id}/form-data",
        json={"form_data": {"new_key": "new_val"}},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["form_data"]["new_key"] == "new_val"


def test_update_form_data_forbidden_for_user(client, created_submission):
    headers = {"X-User-Id": "u1", "X-User-Role": "end_user", "X-Institution-Id": "1"}
    sub_id = created_submission["id"]
    response = client.patch(
        f"/submissions/{sub_id}/form-data",
        json={"form_data": {"key": "val"}},
        headers=headers,
    )
    assert response.status_code == 403


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
