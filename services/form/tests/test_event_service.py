import json
from app.services.event_service import EventService


class FakeRedis:
    def __init__(self):
        self.published = []

    def publish(self, channel, payload):
        self.published.append((channel, payload))

    def ping(self):
        return True


def test_publish_ocr_completed():
    fake = FakeRedis()
    service = EventService(redis_client=fake)
    service.publish_ocr_completed("form-id", 1, 10, 3)

    assert len(fake.published) == 1
    channel, payload = fake.published[0]
    assert channel == "events"
    data = json.loads(payload)
    assert data["event"] == "ocr.completed"
    assert data["field_count"] == 3
    # status defaults to "completed" on success
    assert data["status"] == "completed"


def test_publish_ocr_completed_failed_status():
    fake = FakeRedis()
    service = EventService(redis_client=fake)
    service.publish_ocr_completed("form-id", 1, 10, 0, status="failed")

    _, payload = fake.published[0]
    data = json.loads(payload)
    assert data["status"] == "failed"
    assert data["field_count"] == 0
