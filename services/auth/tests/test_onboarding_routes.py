from app.models.staff_onboarding import StaffCSVRow, StaffCSVUpload


def test_upload_institution_staff_csv_success(client, db_session):
    csv_content = "name,email,role,department\nTester,test@x.com,staff,IT"
    response = client.post(
        "/admin/institutions/1/staff/upload",
        files={"file": ("staff.csv", csv_content, "text/csv")},
        headers={"X-User-Role": "super_admin"},
    )
    assert response.status_code == 200
    assert response.json()["rows_processed"] == 1


def test_list_institution_staff(client, db_session):
    # Setup upload and row
    upload = StaffCSVUpload(institution_id=1, uploaded_by="admin", file_name="test.csv")
    db_session.add(upload)
    db_session.commit()
    db_session.refresh(upload)

    row = StaffCSVRow(
        upload_id=upload.id,
        institution_id=1,
        email="staff@x.com",
        name="Staff",
        role="staff",
        department="IT",
    )
    db_session.add(row)
    db_session.commit()

    response = client.get(
        "/admin/institutions/1/staff",
        headers={"X-User-Role": "admin", "X-Institution-Id": "1"},
    )
    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_list_uploads(client):
    response = client.get("/onboarding/uploads", headers={"X-User-Role": "super_admin"})
    assert response.status_code == 200


def test_upload_staff_csv_invalid_file_type(client):
    response = client.post(
        "/admin/institutions/1/staff/upload",
        files={"file": ("staff.txt", "name,email\ntest,test@x.com", "text/plain")},
        headers={"X-User-Role": "super_admin"},
    )
    assert response.status_code == 400
    assert "Only CSV files are allowed" in response.json()["detail"]


def test_upload_staff_csv_forbidden_for_end_user(client):
    response = client.post(
        "/admin/institutions/1/staff/upload",
        files={"file": ("staff.csv", "name,email\ntest,test@x.com", "text/csv")},
        headers={"X-User-Role": "end_user"},
    )
    assert response.status_code == 403


def test_list_institution_staff_wrong_institution(client, db_session):
    upload = StaffCSVUpload(institution_id=1, uploaded_by="admin", file_name="test.csv")
    db_session.add(upload)
    db_session.commit()
    db_session.refresh(upload)

    row = StaffCSVRow(
        upload_id=upload.id,
        institution_id=1,
        email="staff@x.com",
        name="Staff",
        role="staff",
        department="IT",
    )
    db_session.add(row)
    db_session.commit()

    # Admin from inst 2 tries to list inst 1
    response = client.get(
        "/admin/institutions/1/staff",
        headers={"X-User-Role": "admin", "X-Institution-Id": "2"},
    )
    assert response.status_code == 403


def test_get_staff_row_not_found(client):
    response = client.get(
        "/admin/institutions/1/staff/9999",
        headers={"X-User-Role": "admin", "X-Institution-Id": "1"},
    )
    assert response.status_code == 404


def test_delete_staff_row(client, db_session):
    upload = StaffCSVUpload(institution_id=1, uploaded_by="admin", file_name="test.csv")
    db_session.add(upload)
    db_session.commit()
    db_session.refresh(upload)

    row = StaffCSVRow(
        upload_id=upload.id,
        institution_id=1,
        email="del@x.com",
        name="Staff",
        role="staff",
        department="IT",
    )
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)

    response = client.delete(
        f"/admin/institutions/1/staff/{row.id}",
        headers={"X-User-Role": "admin", "X-Institution-Id": "1"},
    )
    assert response.status_code == 200