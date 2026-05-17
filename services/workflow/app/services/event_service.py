import json
import os
from typing import Optional
import redis


class EventService:
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis = redis_client or redis.Redis.from_url(
            os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            decode_responses=True,
        )

    def publish_workflow_published(
        self,
        workflow_id: str,
        institution_id: int,
        admin_id: int,
        step_count: int,
        published_at: str,
    ) -> None:
        payload = {
            "event": "workflow.published",
            "workflow_id": workflow_id,
            "institution_id": institution_id,
            "admin_id": admin_id,
            "step_count": step_count,
            "published_at": published_at,
        }
        self.redis.publish("events", json.dumps(payload))

    def ping(self) -> bool:
        return bool(self.redis.ping())
