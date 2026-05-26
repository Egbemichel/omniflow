import json
import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session
from app.worker import run_worker, handle_message


def test_handle_message_saves_to_db():
    test_data = {
        "recipient_id": "user-123",
        "event_type": "task_assigned",
        "message": "You have a new task",
    }
    mock_db = MagicMock(spec=Session)

    with patch("app.worker.SessionLocal", return_value=mock_db):
        with patch("app.services.create_notification") as mock_create:
            handle_message(test_data)

            mock_create.assert_called_once_with(
                mock_db,
                recipient_id="user-123",
                event_type="task_assigned",
                message="You have a new task",
            )
            mock_db.close.assert_called()


def test_handle_message_handles_exception_gracefully():
    test_data = {"recipient_id": "u", "event_type": "e", "message": "m"}
    mock_db = MagicMock(spec=Session)

    with patch("app.worker.SessionLocal", return_value=mock_db):
        with patch(
            "app.services.create_notification", side_effect=Exception("DB Error")
        ):
            handle_message(test_data)
            mock_db.close.assert_called()


# Use SystemExit (not caught by `except Exception`) to escape the while True
class _StopWorker(SystemExit):
    pass


class MockPubSub:
    def __init__(self, messages):
        self.messages = messages

    def subscribe(self, channel):
        pass

    def listen(self):
        yield from self.messages
        # SystemExit is NOT caught by `except Exception`, so it
        # escapes the for-loop AND the while-True cleanly
        raise _StopWorker("done")


@patch("app.worker.redis.from_url")  # patch on the module, not the top-level redis
@patch("app.worker.SessionLocal")
@patch("app.worker.time.sleep")
def test_worker_processes_notification_message(
    mock_sleep, mock_session_local, mock_redis_from_url
):
    test_data = {
        "recipient_id": "user-123",
        "event_type": "task_assigned",
        "message": "You have a new task",
    }
    messages = [{"type": "message", "data": json.dumps(test_data)}]

    mock_r = MagicMock()
    mock_r.pubsub.return_value = MockPubSub(messages)
    mock_redis_from_url.return_value = mock_r

    mock_db = MagicMock(spec=Session)
    mock_session_local.return_value = mock_db

    with patch("app.services.create_notification") as mock_create:
        with pytest.raises(_StopWorker):
            run_worker()

        mock_create.assert_called_once_with(
            mock_db,
            recipient_id="user-123",
            event_type="task_assigned",
            message="You have a new task",
        )
        mock_db.close.assert_called()


@patch("app.worker.redis.from_url")  # same fix here
@patch("app.worker.time.sleep")
def test_worker_connection_error_handling(mock_sleep, mock_redis_from_url):
    mock_redis_from_url.side_effect = [
        Exception("Connection failed"),
        _StopWorker("Stop"),
    ]

    with pytest.raises(_StopWorker):
        run_worker()

    assert mock_sleep.called
    assert mock_sleep.call_args[0][0] == 5
