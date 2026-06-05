from app.repositories.form_repository import FormRepository
from sqlalchemy import text


def test_upload_happy_path(admin_client, db_session, upload_dir, monkeypatch):
    # Pre-test schema verification
    if db_session.bind.dialect.name == "postgresql":  # pragma: no cover
        result = db_session.execute(text("SELECT current_schema()")).scalar()
        assert result == "form_schema", f"Expected form_schema, got {result}"

    def fake_extract(self, file_path):
        return [
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
        ]

    published = {}

    def fake_publish(self, form_id, institution_id, admin_id, field_count, status="completed"):
        published["payload"] = {
            "form_id": form_id,
            "institution_id": institution_id,
            "admin_id": admin_id,
            "field_count": field_count,
            "status": status,
        }

    monkeypatch.setattr(
        "app.services.ocr_service.OCRService.extract_fields", fake_extract
    )
    monkeypatch.setattr(
        "app.services.event_service.EventService.publish_ocr_completed", fake_publish
    )

    response = admin_client.post(
        "/forms/upload",
        files={"file": ("test.png", b"fake", "image/png")},
    )
    assert response.status_code == 201
    form_id = response.json()["form_id"]

    repo = FormRepository(db_session)
    form = repo.get_form_any(form_id)
    assert form is not None
    assert form.status == "READY"

    fields = repo.get_fields(form_id)
    assert len(fields) == 2
    assert published["payload"]["field_count"] == 2
    assert published["payload"]["status"] == "completed"


def test_upload_rejects_unsupported_type(admin_client, upload_dir):
    response = admin_client.post(
        "/forms/upload",
        files={"file": ("test.txt", b"data", "text/plain")},
    )
    assert response.status_code == 422


def test_upload_rejects_oversized_file(admin_client, upload_dir, monkeypatch):
    monkeypatch.setenv("MAX_FILE_SIZE_MB", "0")
    response = admin_client.post(
        "/forms/upload",
        files={"file": ("big.pdf", b"data", "application/pdf")},
    )
    assert response.status_code == 413


def test_upload_missing_auth_returns_401(client, upload_dir):
    response = client.post(
        "/forms/upload",
        files={"file": ("test.png", b"fake", "image/png")},
    )
    assert response.status_code == 401

def test_upload_ocr_failure_sets_failed_status(admin_client, db_session, upload_dir, monkeypatch):
    def fake_extract_failure(self, file_path):
        raise RuntimeError("OCR engine crashed")

    published = {}

    def fake_publish(self, form_id, institution_id, admin_id, field_count, status="completed"):
        published["status"] = status
        published["field_count"] = field_count

    monkeypatch.setattr(
        "app.services.ocr_service.OCRService.extract_fields", fake_extract_failure
    )
    monkeypatch.setattr(
        "app.services.event_service.EventService.publish_ocr_completed", fake_publish
    )

    response = admin_client.post(
        "/forms/upload",
        files={"file": ("test.png", b"fake image content", "image/png")},
    )
    assert response.status_code == 201
    form_id = response.json()["form_id"]

    status_response = admin_client.get(f"/forms/{form_id}/status")
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "FAILED"
    # ocr.completed is published with status "failed" on failure
    assert published["status"] == "failed"
    assert published["field_count"] == 0
