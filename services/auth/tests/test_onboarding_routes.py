from app.models.staff_onboarding import StaffCSVRow

def test_upload_institution_staff_csv_success(client, db_session):
    csv_content = "name,email,role,department\nTester,test@x.com,staff,IT"
    response = client.post(
        "/admin/institutions/1/staff/upload",
        files={"file": ("staff.csv", csv_content, "text/csv")},
        headers={"X-User-Role": "super_admin"}
    )
    assert response.status_code == 200
    assert response.json()["rows_processed"] == 1

def test_list_institution_staff(client, db_session):
    # Setup row
    row = StaffCSVRow(institution_id=1, email="staff@x.com", name="Staff", role="staff", department="IT")
    db_session.add(row)
    db_session.commit()
    
    response = client.get(
        "/admin/institutions/1/staff",
        headers={"X-User-Role": "admin", "X-Institution-Id": "1"}
    )
    assert response.status_code == 200
    assert len(response.json()) >= 1

def test_get_staff_row_not_found(client):
    response = client.get(
        "/admin/institutions/1/staff/9999",
        headers={"X-User-Role": "admin", "X-Institution-Id": "1"}
    )
    assert response.status_code == 404

def test_delete_staff_row(client, db_session):
     row = StaffCSVRow(institution_id=1, email="del@x.com", name="Staff", role="staff", department="IT")
     db_session.add(row)
     db_session.commit()
     db_session.refresh(row)
     
     response = client.delete(
         f"/admin/institutions/1/staff/{row.id}",
         headers={"X-User-Role": "admin", "X-Institution-Id": "1"}
     )
     assert response.status_code == 200

def test_list_uploads(client):
    response = client.get("/onboarding/uploads", headers={"X-User-Role": "super_admin"})
    assert response.status_code == 200
