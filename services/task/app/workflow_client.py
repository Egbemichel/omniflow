"""
HTTP client for the Workflow Service.
In tests this module is mocked via conftest.py.
In production it calls the real workflow service URL.
"""

import os
import httpx

WORKFLOW_SERVICE_URL = os.getenv("WORKFLOW_SERVICE_URL", "http://localhost:8003")


def initialise_submission(workflow_id: str, submission_id: str) -> dict:
    """Tell the Workflow Service to initialise state for a new submission."""
    response = httpx.post(
        f"{WORKFLOW_SERVICE_URL}/workflows/{workflow_id}/transition",
        json={"current_step_id": None, "action": "START"},
        headers={"X-User-Id": "task-service", "X-User-Role": "admin"},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def advance_submission(workflow_id: str, current_step_id: str, action: str) -> dict:
    """Tell the Workflow Service to advance the submission to the next step."""
    response = httpx.post(
        f"{WORKFLOW_SERVICE_URL}/workflows/{workflow_id}/transition",
        json={"current_step_id": current_step_id, "action": action},
        headers={"X-User-Id": "task-service", "X-User-Role": "admin"},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()
