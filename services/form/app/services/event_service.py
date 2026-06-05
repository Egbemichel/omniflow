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

    def publish_ocr_completed(
        self,
        form_id: str,
        institution_id: int,
        admin_id: int,
        field_count: int,
        status: str = "completed",
    ) -> None:
        payload = {
            "event": "ocr.completed",
            "form_id": form_id,
            "institution_id": institution_id,
            "admin_id": admin_id,
            "field_count": field_count,
            "status": status,
        }
        self.redis.publish("events", json.dumps(payload))

    def ping(self) -> bool:
        return bool(self.redis.ping())
