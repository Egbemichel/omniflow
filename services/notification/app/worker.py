import redis
import json
import os
import threading
import time
from sqlalchemy.orm import Session
from app.database import SessionLocal, DATABASE_URL
from app import services

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


def run_worker():
    """Background worker to consume Redis messages and save to DB."""
    while True:
        try:
            r = redis.from_url(REDIS_URL)
            pubsub = r.pubsub()
            pubsub.subscribe("notifications")
            print("[Notification Worker] Subscribed to 'notifications' channel.")

            for message in pubsub.listen():
                if message["type"] == "message":
                    data = json.loads(message["data"])
                    print(f"[Notification Worker] Received event: {data}")

                    db: Session = SessionLocal()
                    try:
                        # If PostgreSQL, we need to set search_path
                        if not DATABASE_URL.startswith("sqlite"):
                            from sqlalchemy import text

                            schema = os.getenv("DATABASE_SCHEMA", "notification_schema")
                            db.execute(text(f"SET search_path TO {schema}"))

                        services.create_notification(
                            db,
                            recipient_id=data["recipient_id"],
                            event_type=data["event_type"],
                            message=data["message"],
                        )
                        print(
                            f"[Notification Worker] Saved notification for {data['recipient_id']}"
                        )
                    except Exception as e:
                        print(f"[Notification Worker] Error saving notification: {e}")
                    finally:
                        db.close()
        except Exception as e:
            print(f"[Notification Worker] Connection error: {e}. Retrying in 5s...")
            time.sleep(5)


def start_worker():
    thread = threading.Thread(target=run_worker, daemon=True)
    thread.start()
