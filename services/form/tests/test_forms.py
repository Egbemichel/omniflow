import os

from app.repositories.form_repository import FormRepository


def test_file_preview_returns_uploaded_file(admin_client, db_session, create_form):
    form = create_form(status="READY")
    with open(form.file_path, "wb") as fh:
        fh.write(b"%PDF-1.4 fake pdf bytes")

    try:
        response = admin_client.get(f"/forms/{form.id}/file")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/pdf")
        assert response.content == b"%PDF-1.4 fake pdf bytes"
    finally:
        os.remove(form.file_path)


def test_file_preview_missing_file_returns_404(admin_client, create_form):
    form = create_form(status="READY")  # file_path points at a non-existent file
    response = admin_client.get(f"/forms/{form.id}/file")
    assert response.status_code == 404


def test_file_preview_cross_institution_forbidden(other_inst_client, create_form):
    form = create_form(institution_id=1, status="READY")
    response = other_inst_client.get(f"/forms/{form.id}/file")
    assert response.status_code == 403


def test_status_ready_returns_fields(admin_client, db_session, create_form):
    form = create_form(status="READY")
    repo = FormRepository(db_session)
    repo.replace_fields(
        form.id,
        [
            {
                "field_name": "Name",
                "field_type": "text",
                "required": False,
                "position": 0,
            },
            {
                "field_name": "Date",
                "field_type": "date",
                "required": False,
                "position": 1,
            },
        ],
    )

    response = admin_client.get(f"/forms/{form.id}/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "READY"
    assert data["field_count"] == 2


def test_schema_patch_confirms(admin_client, db_session, create_form):
    form = create_form(status="READY")
    response = admin_client.patch(
        f"/forms/{form.id}/schema",
        json={
            "fields": [
                {
                    "field_name": "Full Name",
                    "field_type": "text",
                    "required": True,
                    "position": 0,
                }
            ]
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "CONFIRMED"

    conflict = admin_client.patch(
        f"/forms/{form.id}/schema",
        json={
            "fields": [
                {
                    "field_name": "X",
                    "field_type": "text",
                    "required": False,
                    "position": 0,
                }
            ]
        },
    )
    assert conflict.status_code == 409


def test_list_scoped_by_institution(admin_client, db_session, create_form):
    create_form(institution_id=1)
    create_form(institution_id=2)

    response = admin_client.get("/forms")
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1


def test_cross_institution_access_returns_403(admin_client, db_session, create_form):
    form = create_form(institution_id=2)
    response = admin_client.get(f"/forms/{form.id}/status")
    assert response.status_code == 403


def test_suggest_workflow_stub(admin_client, db_session, create_form):
    form = create_form(institution_id=1)
    response = admin_client.get(f"/forms/{form.id}/suggest-workflow")
    assert response.status_code == 200
    data = response.json()
    assert "steps" in data
    assert isinstance(data["steps"], list)
    assert len(data["steps"]) > 0


def test_get_schema_returns_fields(admin_client, db_session, create_form):
    form = create_form(status="READY")
    repo = FormRepository(db_session)
    repo.replace_fields(
        form.id,
        [
            {
                "field_name": "Patient Name",
                "field_type": "text",
                "required": True,
                "position": 0,
            },
            {
                "field_name": "Date of Birth",
                "field_type": "date",
                "required": False,
                "position": 1,
            },
        ],
    )
    db_session.commit()

    response = admin_client.get(f"/forms/{form.id}/schema")
    assert response.status_code == 200
    data = response.json()
    assert "fields" in data
    assert len(data["fields"]) == 2
    field_names = [f["field_name"] for f in data["fields"]]
    assert "Patient Name" in field_names
    assert "Date of Birth" in field_names


def test_get_schema_returns_404_for_nonexistent_form(admin_client):
    response = admin_client.get("/forms/00000000-0000-0000-0000-000000000000/schema")
    assert response.status_code == 404


def test_get_status_returns_404_for_nonexistent_form(admin_client):
    response = admin_client.get("/forms/00000000-0000-0000-0000-000000000000/status")
    assert response.status_code == 404


def test_list_forms_pagination(admin_client, db_session, create_form):
    create_form(institution_id=1)
    create_form(institution_id=1)
    create_form(institution_id=1)

    response = admin_client.get("/forms?page=1&page_size=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 2


def test_list_forms_second_page(admin_client, db_session, create_form):
    create_form(institution_id=1)
    create_form(institution_id=1)
    create_form(institution_id=1)

    response = admin_client.get("/forms?page=2&page_size=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1


def test_schema_patch_returns_404_for_nonexistent_form(admin_client):
    response = admin_client.patch(
        "/forms/00000000-0000-0000-0000-000000000000/schema",
        json={
            "fields": [
                {
                    "field_name": "Name",
                    "field_type": "text",
                    "required": False,
                    "position": 0,
                }
            ]
        },
    )
    assert response.status_code == 404


def test_status_processing_returns_no_fields(admin_client, db_session, create_form):
    form = create_form(status="PROCESSING")

    response = admin_client.get(f"/forms/{form.id}/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "PROCESSING"
    assert data["field_count"] == 0
