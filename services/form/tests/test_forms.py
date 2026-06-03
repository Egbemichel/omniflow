from app.repositories.form_repository import FormRepository


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
