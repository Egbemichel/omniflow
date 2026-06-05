from app.models.staff_onboarding import StaffCSVRow
from app.repositories.user_repository import UserRepository
from app.services.jwt_service import create_access_token, decode_token


def _auth_header(user):
    token = create_access_token(
        {
            "sub": user.id,
            "email": user.email,
            "role": user.role,
            "institution_id": user.institution_id,
        }
    )
    return {"Authorization": f"Bearer {token}"}


def test_staff_csv_upload_parses_and_scopes_rows(client, db_session, create_user):
    admin = create_user(
        db_session,
        email="admin@hospital.com",
        role="institution_admin",
        institution_id=42,
    )
    csv_content = (
        "name,email,role,department,phone,employee_id\n"
        "Alice Smith,alice@hospital.com,workflow_actor,Pediatrics,555-0100,E-1\n"
    )

    response = client.post(
        "/admin/institutions/42/staff/upload",
        headers=_auth_header(admin),
        files={"file": ("staff.csv", csv_content, "text/csv")},
    )

    assert response.status_code == 200
    assert response.json()["rows_processed"] == 1

    rows = db_session.query(StaffCSVRow).filter(StaffCSVRow.institution_id == 42).all()
    assert len(rows) == 1
    assert rows[0].email == "alice@hospital.com"
    assert rows[0].extra_fields["employee_id"] == "E-1"


def test_staff_csv_upload_rejects_missing_required_columns(
    client, db_session, create_user
):
    admin = create_user(
        db_session,
        email="admin@hospital.com",
        role="institution_admin",
        institution_id=42,
    )

    response = client.post(
        "/admin/institutions/42/staff/upload",
        headers=_auth_header(admin),
        files={"file": ("staff.csv", "name,email\nAlice,a@x.com\n", "text/csv")},
    )

    assert response.status_code == 400
    assert "missing required columns" in response.json()["detail"]


def test_staff_csv_upload_rejects_duplicate_emails(client, db_session, create_user):
    admin = create_user(
        db_session,
        email="admin@hospital.com",
        role="institution_admin",
        institution_id=42,
    )
    csv_content = (
        "name,email,role,department\n"
        "Alice,alice@hospital.com,staff,Pediatrics\n"
        "Alice Two,alice@hospital.com,staff,Pediatrics\n"
    )

    response = client.post(
        "/admin/institutions/42/staff/upload",
        headers=_auth_header(admin),
        files={"file": ("staff.csv", csv_content, "text/csv")},
    )

    assert response.status_code == 400
    assert "duplicate email" in response.json()["detail"]


def test_login_matching_staff_csv_sets_role_and_institution(
    client, db_session, create_user, monkeypatch
):
    admin = create_user(
        db_session,
        email="admin@hospital.com",
        role="institution_admin",
        institution_id=42,
    )
    csv_content = (
        "name,email,role,department\n"
        "Alice Smith,alice@hospital.com,workflow_actor,Pediatrics\n"
    )
    upload = client.post(
        "/admin/institutions/42/staff/upload",
        headers=_auth_header(admin),
        files={"file": ("staff.csv", csv_content, "text/csv")},
    )
    assert upload.status_code == 200

    monkeypatch.setattr(
        "app.routes.oauth.exchange_google_code",
        lambda *a, **kw: {
            "email": "alice@hospital.com",
            "oauth_id": "google-alice",
            "full_name": "Alice OAuth",
        },
    )

    response = client.post(
        "/auth/google",
        json={"code": "test", "redirect_uri": "https://app/callback"},
    )

    assert response.status_code == 200
    payload = decode_token(response.json()["access_token"])
    assert payload["institution_id"] == 42
    assert payload["role"] == "staff"

    repo = UserRepository(db_session)
    user = repo.get_by_email("alice@hospital.com")
    assert user.full_name == "Alice Smith"
    assert user.institution_id == 42

    row = db_session.query(StaffCSVRow).filter_by(email="alice@hospital.com").first()
    assert row.matched_user_id == user.id


def test_login_custom_actor_type_maps_to_staff_role(
    client, db_session, create_user, monkeypatch
):
    """A custom CSV role_label (e.g. "NURSE") is an actor type, not a system role.

    The user's system role must be "staff" and the label must be stored as the
    actor_type — never leaked into the system-role field.
    """
    admin = create_user(
        db_session,
        email="admin@hospital.com",
        role="institution_admin",
        institution_id=42,
    )
    csv_content = (
        "name,email,role,department\n"
        "Nurse Joy,joy@hospital.com,NURSE,Pediatrics\n"
    )
    upload = client.post(
        "/admin/institutions/42/staff/upload",
        headers=_auth_header(admin),
        files={"file": ("staff.csv", csv_content, "text/csv")},
    )
    assert upload.status_code == 200

    monkeypatch.setattr(
        "app.routes.oauth.exchange_google_code",
        lambda *a, **kw: {
            "email": "joy@hospital.com",
            "oauth_id": "google-joy",
            "full_name": "Nurse Joy",
        },
    )

    response = client.post(
        "/auth/google",
        json={"code": "test", "redirect_uri": "https://app/callback"},
    )

    assert response.status_code == 200
    payload = decode_token(response.json()["access_token"])
    assert payload["role"] == "staff"
    assert payload["actor_type"] == "NURSE"

    repo = UserRepository(db_session)
    user = repo.get_by_email("joy@hospital.com")
    assert user.role == "staff"
    assert user.actor_type == "NURSE"


def test_staff_rows_cannot_cross_institution(client, db_session, create_user):
    admin = create_user(
        db_session,
        email="admin@hospital.com",
        role="institution_admin",
        institution_id=42,
    )
    other_admin = create_user(
        db_session,
        email="admin@school.com",
        role="institution_admin",
        institution_id=7,
    )
    csv_content = (
        "name,email,role,department\n"
        "Alice Smith,alice@hospital.com,workflow_actor,Pediatrics\n"
    )
    client.post(
        "/admin/institutions/42/staff/upload",
        headers=_auth_header(admin),
        files={"file": ("staff.csv", csv_content, "text/csv")},
    )

    forbidden = client.get(
        "/admin/institutions/42/staff",
        headers=_auth_header(other_admin),
    )
    assert forbidden.status_code == 403

    own_rows = client.get(
        "/admin/institutions/7/staff",
        headers=_auth_header(other_admin),
    )
    assert own_rows.status_code == 200
    assert own_rows.json() == []
