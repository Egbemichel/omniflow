def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200


def test_admin_can_create_notification(client):
    response = client.post(
        "/notifications",
        json={
            "recipient_id": "user-123",
            "event_type": "task_assigned",
            "message": "New task for you",
        },
        headers={"X-User-Role": "admin"},
    )
    assert response.status_code == 201
    assert response.json()["recipient_id"] == "user-123"


def test_user_cannot_create_notification(client):
    response = client.post(
        "/notifications",
        json={
            "recipient_id": "user-123",
            "event_type": "task_assigned",
            "message": "New task for you",
        },
        headers={"X-User-Role": "end_user"},
    )
    assert response.status_code == 403


def test_get_my_notifications(client):
    # Setup: admin creates one
    client.post(
        "/notifications",
        json={
            "recipient_id": "user-123",
            "event_type": "task_assigned",
            "message": "Note 1",
        },
        headers={"X-User-Role": "admin"},
    )

    # Check
    response = client.get("/notifications", headers={"X-User-Id": "user-123"})
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["message"] == "Note 1"


def test_mark_read(client):
    # Setup
    r = client.post(
        "/notifications",
        json={
            "recipient_id": "user-123",
            "event_type": "task_assigned",
            "message": "Note 1",
        },
        headers={"X-User-Role": "admin"},
    )
    notif_id = r.json()["id"]

    # Mark read
    response = client.patch(
        f"/notifications/{notif_id}/read", headers={"X-User-Id": "user-123"}
    )
    assert response.status_code == 200
    assert response.json()["is_read"] is True


def test_mark_read_nonexistent(client):
    response = client.patch(
        "/notifications/missing/read", headers={"X-User-Id": "user-123"}
    )
    assert response.status_code == 404


def test_get_notifications_unauthenticated(client):
    response = client.get("/notifications")
    assert response.status_code == 401


def test_mark_read_unauthenticated(client):
    response = client.patch("/notifications/123/read")
    assert response.status_code == 401


def test_validate_schema_isolation(client):
    from app.database import SessionLocal
    from app.schema_utils import validate_schema_isolation
    import os

    if not os.getenv("DATABASE_URL", "").startswith("sqlite"):
        db = SessionLocal()
        try:
            validate_schema_isolation(db)
        finally:
            db.close()
