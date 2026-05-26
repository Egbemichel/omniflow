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

    # Mock DB session
    mock_db = MagicMock(spec=Session)

    with patch("app.worker.SessionLocal", return_value=mock_db):
        with patch("app.services.create_notification") as mock_create:
            handle_message(test_data)

            # Verify database interaction
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
            # Should not raise exception
            handle_message(test_data)
            mock_db.close.assert_called()


class MockPubSub:
    def __init__(self, messages):
        self.messages = messages

    def subscribe(self, channel):
        pass

    def listen(self):
        for m in self.messages:
            yield m
        # Break the infinite loop in run_worker by raising an exception after messages are consumed
        raise StopIteration("End of mock messages")


@patch("redis.from_url")
@patch("app.worker.SessionLocal")
@patch("app.worker.time.sleep")  # To speed up the exception path if it hits it
def test_worker_processes_notification_message(
    mock_sleep, mock_session_local, mock_redis_from_url
):
    # Setup mock messages
    test_data = {
        "recipient_id": "user-123",
        "event_type": "task_assigned",
        "message": "You have a new task",
    }
    messages = [{"type": "message", "data": json.dumps(test_data)}]

    mock_r = MagicMock()
    mock_pubsub = MockPubSub(messages)
    mock_r.pubsub.return_value = mock_pubsub
    mock_redis_from_url.return_value = mock_r

    # Mock DB session
    mock_db = MagicMock(spec=Session)
    mock_session_local.return_value = mock_db

    # Mock services.create_notification
    with patch("app.services.create_notification") as mock_create:
        with pytest.raises(StopIteration):
            run_worker()

        # Verify database interaction
        mock_create.assert_called_once_with(
            mock_db,
            recipient_id="user-123",
            event_type="task_assigned",
            message="You have a new task",
        )
        mock_db.close.assert_called()


@patch("redis.from_url")
@patch("app.worker.time.sleep")
def test_worker_connection_error_handling(mock_sleep, mock_redis_from_url):
    # Simulate a connection error then a stop
    mock_redis_from_url.side_effect = [
        Exception("Connection failed"),
        StopIteration("Stop"),
    ]

    with pytest.raises(StopIteration):
        run_worker()

    assert mock_sleep.called
    assert mock_sleep.call_args[0][0] == 5
