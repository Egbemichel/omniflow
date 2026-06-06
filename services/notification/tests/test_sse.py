import json
import pytest
from app.sse import _frame, _ui_events, _authenticate
from unittest.mock import AsyncMock, patch

def test_frame():
    event = "test_event"
    data = {"foo": "bar"}
    expected = 'event: test_event\ndata: {"foo": "bar"}\n\n'
    assert _frame(event, data) == expected

def test_ui_events_ocr_completed():
    user = {"institution_id": 1, "user_id": "u1", "role": "admin"}
    payload = {"institution_id": 1, "event": "ocr.completed", "foo": "bar"}
    events = _ui_events("events", payload, user)
    assert events == [("form.updated", payload)]

def test_ui_events_ocr_different_institution():
    user = {"institution_id": 1}
    payload = {"institution_id": 2, "event": "ocr.completed"}
    events = _ui_events("events", payload, user)
    assert events == []

def test_ui_events_notification_addressed_to_user():
    user = {"user_id": "user-123", "role": "staff", "institution_id": 1}
    payload = {"recipient_id": "user-123", "event_type": "task_assigned", "msg": "hi"}
    events = _ui_events("notifications", payload, user)
    assert ("notification.new", payload) in events
    assert ("task.updated", payload) in events

def test_ui_events_notification_addressed_to_role():
    user = {"user_id": "u1", "role": "staff", "institution_id": 1}
    payload = {"recipient_id": "staff", "event_type": "task_assigned"}
    events = _ui_events("notifications", payload, user)
    assert ("notification.new", payload) in events

def test_ui_events_notification_addressed_to_actor_type():
    user = {"user_id": "u1", "role": "staff", "actor_type": "NURSE", "institution_id": 1}
    payload = {"recipient_id": "nurse", "event_type": "task_assigned"}
    events = _ui_events("notifications", payload, user)
    assert ("notification.new", payload) in events

def test_ui_events_workflow_completed():
    user = {"user_id": "u1", "role": "end_user", "institution_id": 1}
    payload = {"recipient_id": "u1", "event_type": "workflow_completed"}
    events = _ui_events("notifications", payload, user)
    assert ("submission.updated", payload) in events

@pytest.mark.asyncio
async def test_authenticate_success():
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = AsyncMock(status_code=200, json=lambda: {"user_id": "1"})
        user = await _authenticate("valid_token")
        assert user == {"user_id": "1"}

@pytest.mark.asyncio
async def test_authenticate_fail():
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = AsyncMock(status_code=401)
        user = await _authenticate("bad_token")
        assert user is None

@pytest.mark.asyncio
async def test_authenticate_empty():
    user = await _authenticate("")
    assert user is None
