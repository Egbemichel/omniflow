import base64

import pytest

from app.models.submission import FormFieldValue, FormSubmission
from app.repositories.form_repository import FormRepository


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def published_form(create_form, db_session):
    """A CONFIRMED form that has been published."""
    form = create_form(institution_id=1, status="CONFIRMED")
    repo = FormRepository(db_session)
    return repo.publish_form(form)


@pytest.fixture
def published_form_other_inst(create_form, db_session):
    """A published form belonging to institution 2."""
    form = create_form(institution_id=2, status="CONFIRMED")
    repo = FormRepository(db_session)
    return repo.publish_form(form)


# ---------------------------------------------------------------------------
# POST /forms/{form_id}/submit
# ---------------------------------------------------------------------------


def test_submit_form_returns_201(client, published_form):
    response = client.post(
        f"/forms/{published_form.id}/submit",
        json={
            "submitter_id": "patient-1",
            "field_values": [
                {"field_name": "Full Name", "value": "Marie Atanga"},
            ],
        },
    )
    assert response.status_code == 201


def test_submit_triggers_workflow_via_task_service(
    client, published_form, mock_task_client
):
    response = client.post(
        f"/forms/{published_form.id}/submit",
        json={
            "submitter_id": "patient-9",
            "field_values": [{"field_name": "Full Name", "value": "Ada"}],
        },
    )
    assert response.status_code == 201
    mock_task_client.assert_called_once()
    kwargs = mock_task_client.call_args.kwargs
    assert kwargs["form_id"] == published_form.id
    assert kwargs["form_data"] == {"Full Name": "Ada"}
    assert kwargs["submitter_id"] == "patient-9"
    data = response.json()
    assert data["form_id"] == published_form.id
    assert data["status"] == "SUBMITTED"
    assert "submission_id" in data


def test_submit_form_persists_submission_and_field_values(client, published_form, db_session):
    response = client.post(
        f"/forms/{published_form.id}/submit",
        json={
            "submitter_id": "patient-1",
            "field_values": [
                {"field_name": "Full Name", "value": "Marie Atanga"},
                {"field_name": "Date of Birth", "value": "1990-01-15"},
            ],
        },
    )
    assert response.status_code == 201
    submission_id = response.json()["submission_id"]

    db_session.expire_all()
    submission = db_session.query(FormSubmission).filter(
        FormSubmission.id == submission_id
    ).first()
    assert submission is not None
    assert submission.institution_id == published_form.institution_id
    assert submission.submitter_id == "patient-1"

    values = (
        db_session.query(FormFieldValue)
        .filter(FormFieldValue.submission_id == submission_id)
        .all()
    )
    stored = {v.field_name: v.value for v in values}
    assert stored["Full Name"] == "Marie Atanga"
    assert stored["Date of Birth"] == "1990-01-15"


def test_submit_derives_institution_id_from_form(client, published_form, db_session):
    """institution_id on the submission must match the form's institution, not a header."""
    response = client.post(
        f"/forms/{published_form.id}/submit",
        json={"field_values": []},
    )
    assert response.status_code == 201
    submission_id = response.json()["submission_id"]

    db_session.expire_all()
    submission = db_session.query(FormSubmission).filter(
        FormSubmission.id == submission_id
    ).first()
    assert submission.institution_id == published_form.institution_id


def test_submit_anonymous_when_no_submitter_id(client, published_form, db_session):
    response = client.post(
        f"/forms/{published_form.id}/submit",
        json={"field_values": []},
    )
    assert response.status_code == 201
    submission_id = response.json()["submission_id"]

    db_session.expire_all()
    submission = db_session.query(FormSubmission).filter(
        FormSubmission.id == submission_id
    ).first()
    assert submission.submitter_id == "anonymous"


def test_submit_empty_field_values_is_valid(client, published_form):
    response = client.post(
        f"/forms/{published_form.id}/submit",
        json={"submitter_id": "user-1", "field_values": []},
    )
    assert response.status_code == 201


def test_submit_unpublished_form_returns_409(client, create_form):
    form = create_form(institution_id=1, status="CONFIRMED")
    response = client.post(
        f"/forms/{form.id}/submit",
        json={"field_values": []},
    )
    assert response.status_code == 409


def test_submit_nonexistent_form_returns_404(client):
    response = client.post(
        "/forms/00000000-0000-0000-0000-000000000000/submit",
        json={"field_values": []},
    )
    assert response.status_code == 404


def test_submit_requires_no_auth(client, published_form):
    """Public endpoint — no Authorization header needed."""
    response = client.post(
        f"/forms/{published_form.id}/submit",
        json={"field_values": []},
    )
    assert response.status_code == 201


# ---------------------------------------------------------------------------
# GET /forms/{form_id}/submissions
# ---------------------------------------------------------------------------


def test_list_submissions_returns_paginated(admin_client, published_form, db_session):
    repo = FormRepository(db_session)
    for i in range(3):
        repo.create_submission(
            form_id=published_form.id,
            institution_id=1,
            submitter_id=f"user-{i}",
            field_values=[],
        )

    response = admin_client.get(f"/forms/{published_form.id}/submissions?page=1&page_size=2")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["items"]) == 2
    assert data["page"] == 1
    assert data["page_size"] == 2


def test_list_submissions_second_page(admin_client, published_form, db_session):
    repo = FormRepository(db_session)
    for i in range(3):
        repo.create_submission(
            form_id=published_form.id,
            institution_id=1,
            submitter_id=f"user-{i}",
            field_values=[],
        )

    response = admin_client.get(f"/forms/{published_form.id}/submissions?page=2&page_size=2")
    assert response.status_code == 200
    assert len(response.json()["items"]) == 1


def test_list_submissions_empty(admin_client, published_form):
    response = admin_client.get(f"/forms/{published_form.id}/submissions")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []


def test_list_submissions_admin_only(user_client, published_form):
    response = user_client.get(f"/forms/{published_form.id}/submissions")
    assert response.status_code == 403


def test_list_submissions_unauthenticated_returns_401(client, published_form):
    response = client.get(f"/forms/{published_form.id}/submissions")
    assert response.status_code == 401


def test_list_submissions_cross_institution_returns_403(
    admin_client, published_form_other_inst
):
    response = admin_client.get(f"/forms/{published_form_other_inst.id}/submissions")
    assert response.status_code == 403


def test_list_submissions_nonexistent_form_returns_404(admin_client):
    response = admin_client.get("/forms/00000000-0000-0000-0000-000000000000/submissions")
    assert response.status_code == 404


def test_list_submissions_item_shape(admin_client, published_form, db_session):
    repo = FormRepository(db_session)
    repo.create_submission(
        form_id=published_form.id,
        institution_id=1,
        submitter_id="patient-42",
        field_values=[],
    )

    response = admin_client.get(f"/forms/{published_form.id}/submissions")
    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["form_id"] == published_form.id
    assert item["submitter_id"] == "patient-42"
    assert item["status"] == "SUBMITTED"
    assert "submission_id" in item
    assert "submitted_at" in item


# ---------------------------------------------------------------------------
# GET /forms/{form_id}/qr
# ---------------------------------------------------------------------------


def test_qr_returns_200_with_base64(admin_client, published_form):
    response = admin_client.get(f"/forms/{published_form.id}/qr")
    assert response.status_code == 200
    data = response.json()
    assert data["form_id"] == published_form.id
    assert "qr_code_base64" in data
    assert "url" in data


def test_qr_base64_decodes_to_valid_png(admin_client, published_form):
    response = admin_client.get(f"/forms/{published_form.id}/qr")
    assert response.status_code == 200
    raw = base64.b64decode(response.json()["qr_code_base64"])
    assert raw[:4] == b"\x89PNG"


def test_qr_url_contains_form_id(admin_client, published_form):
    response = admin_client.get(f"/forms/{published_form.id}/qr")
    assert response.status_code == 200
    assert published_form.id in response.json()["url"]


def test_qr_url_uses_domain_env_var(admin_client, published_form, monkeypatch):
    monkeypatch.setenv("DOMAIN", "forms.hospital.cm")
    response = admin_client.get(f"/forms/{published_form.id}/qr")
    assert response.status_code == 200
    assert "forms.hospital.cm" in response.json()["url"]


def test_qr_unpublished_form_returns_409(admin_client, create_form):
    form = create_form(institution_id=1, status="CONFIRMED")
    response = admin_client.get(f"/forms/{form.id}/qr")
    assert response.status_code == 409


def test_qr_admin_only(user_client, published_form):
    response = user_client.get(f"/forms/{published_form.id}/qr")
    assert response.status_code == 403


def test_qr_unauthenticated_returns_401(client, published_form):
    response = client.get(f"/forms/{published_form.id}/qr")
    assert response.status_code == 401


def test_qr_cross_institution_returns_403(admin_client, published_form_other_inst):
    response = admin_client.get(f"/forms/{published_form_other_inst.id}/qr")
    assert response.status_code == 403


def test_qr_nonexistent_form_returns_404(admin_client):
    response = admin_client.get("/forms/00000000-0000-0000-0000-000000000000/qr")
    assert response.status_code == 404
