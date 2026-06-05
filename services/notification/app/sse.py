"""Server-Sent Events (SSE) endpoint.

Bridges the existing Redis events to connected browsers so the UI re-renders the
moment something actually changes — no polling. The stream carries only lightweight
"refetch hint" events (a type + the raw payload); the browser then refetches the
affected view through the normal authorized endpoints, so the stream itself never
exposes anything the user couldn't already fetch.

Auth: EventSource can't send headers, so the JWT is passed as a `?token=` query
param and validated once (at connect) against the Auth Service.
"""

import json
import os

import httpx
from fastapi import APIRouter, HTTPException, Request
from redis import asyncio as aioredis
from starlette.responses import StreamingResponse

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://localhost:8001")

# Redis channels the rest of the system publishes to.
CHANNELS = ["events", "notifications"]
KEEPALIVE_SECONDS = 15

router = APIRouter()


async def _authenticate(token: str) -> dict | None:
    if not token:
        return None
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(
                f"{AUTH_SERVICE_URL}/auth/verify",
                headers={"Authorization": f"Bearer {token}"},
            )
    except httpx.RequestError:
        return None
    if resp.status_code != 200:
        return None
    return resp.json()


def _ui_events(channel: str, payload: dict, user: dict) -> list[tuple[str, dict]]:
    """Map one raw Redis event to the UI hints this user should receive."""
    out: list[tuple[str, dict]] = []
    if channel == "events":
        # Domain events (form/workflow) carry institution_id — scope by it.
        if str(payload.get("institution_id")) != str(user.get("institution_id")):
            return out
        event = payload.get("event")
        if event == "ocr.completed":
            out.append(("form.updated", payload))
        elif event == "workflow.published":
            out.append(("workflow.updated", payload))
    elif channel == "notifications":
        # Per-recipient notifications: deliver if addressed to this user's id,
        # system role, or actor type (matched case-insensitively).
        recipient = str(payload.get("recipient_id") or "").lower()
        targets = {
            str(user.get("user_id")).lower(),
            str(user.get("role")).lower(),
            str(user.get("actor_type") or "").lower(),
        }
        if recipient and recipient in targets:
            out.append(("notification.new", payload))
            event_type = payload.get("event_type")
            if event_type == "task_assigned":
                out.append(("task.updated", payload))
            elif event_type == "workflow_completed":
                out.append(("submission.updated", payload))
    return out


def _frame(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def _close(obj) -> None:
    for name in ("aclose", "close"):
        method = getattr(obj, name, None)
        if method is None:
            continue
        try:
            result = method()
            if hasattr(result, "__await__"):
                await result
            return
        except Exception:
            return


@router.get("/events")
async def events(request: Request, token: str = ""):
    user = await _authenticate(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or missing token")

    async def stream():
        redis = aioredis.from_url(REDIS_URL, decode_responses=True)
        pubsub = redis.pubsub()
        await pubsub.subscribe(*CHANNELS)
        try:
            yield ": connected\n\n"
            while True:
                if await request.is_disconnected():
                    break
                message = await pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=KEEPALIVE_SECONDS
                )
                if message is None:
                    yield ": keepalive\n\n"  # heartbeat keeps proxies from idling out
                    continue
                try:
                    payload = json.loads(message["data"])
                except (ValueError, TypeError):
                    continue
                for ui_type, data in _ui_events(message["channel"], payload, user):
                    yield _frame(ui_type, data)
        finally:
            await _close(pubsub)
            await _close(redis)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
