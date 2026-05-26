import json
from app.services.event_service import EventService


class FakeRedis:
    def __init__(self):
        self.published = []

    def publish(self, channel, payload):
        self.published.append((channel, payload))

    def ping(self):
        return True


def test_publish_workflow_published():
    fake = FakeRedis()
    service = EventService(redis_client=fake)
    service.publish_workflow_published("wf-id", 1, 42, 3, "2026-05-17T00:00:00Z")

    assert len(fake.published) == 1
    channel, payload = fake.published[0]
    assert channel == "events"
    data = json.loads(payload)
    assert data["event"] == "workflow.published"
    assert data["step_count"] == 3
