from app.models.staff_onboarding import StaffCSVRow, StaffCSVUpload, UploadStatus


def _make_staff_row(db_session, institution_id=1, email="staff@x.com"):
    """Create a StaffCSVRow with its required parent upload."""
    upload = StaffCSVUpload(
        institution_id=institution_id,
        uploaded_by="admin-1",
        file_name="staff.csv",
        row_count=1,
        upload_status=UploadStatus.PROCESSED,
    )
    db_session.add(upload)
    db_session.flush()

    row = StaffCSVRow(
        upload_id=upload.id,
        institution_id=institution_id,
        email=email,
        name="Staff",
        role="staff",
        department="IT",
    )
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    return row


def test_upload_institution_staff_csv_success(client, as_user):
    as_user(role="super_admin")
    csv_content = "name,email,role,department\nTester,test@x.com,staff,IT"
    response = client.post(
        "/admin/institutions/1/staff/upload",
        files={"file": ("staff.csv", csv_content, "text/csv")},
    )
    assert response.status_code == 200
    assert response.json()["rows_processed"] == 1


def test_list_institution_staff(client, db_session, as_user):
    _make_staff_row(db_session, institution_id=1)
    as_user(role="admin", institution_id=1)
    response = client.get("/admin/institutions/1/staff")
    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_get_staff_row_not_found(client, as_user):
    as_user(role="admin", institution_id=1)
    response = client.get("/admin/institutions/1/staff/9999")
    assert response.status_code == 404


def test_delete_staff_row(client, db_session, as_user):
    row = _make_staff_row(db_session, institution_id=1, email="del@x.com")
    as_user(role="admin", institution_id=1)
    response = client.delete(f"/admin/institutions/1/staff/{row.id}")
    assert response.status_code == 200


def test_list_uploads(client, as_user):
    as_user(role="super_admin")
    response = client.get("/onboarding/uploads")
    assert response.status_code == 200
