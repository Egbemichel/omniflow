"""HTTP client for the Task Service.

When a public (QR) form submission arrives, the Form Service asks the Task Service
to start the linked workflow. This is best-effort: the form submission is recorded
regardless of whether the workflow kickoff succeeds, so form availability never
depends on the Task/Workflow services being up.
"""

import os
from typing import Any, Dict, Optional

import httpx

TASK_SERVICE_URL = os.getenv("TASK_SERVICE_URL", "http://localhost:8004")


def start_workflow_submission(
    form_id: str,
    institution_id: int,
    form_data: Dict[str, Any],
    submitter_id: str,
) -> Optional[dict]:
    """Ask the Task Service to start the workflow for this form.

    Returns the task submission dict on success, or None if no workflow is linked
    or the Task Service is unreachable.
    """
    try:
        response = httpx.post(
            f"{TASK_SERVICE_URL}/submissions",
            json={
                "form_id": form_id,
                "form_data": form_data,
                "submitter_id": submitter_id,
            },
            headers={
                "X-User-Id": submitter_id,
                "X-User-Role": "end_user",
                "X-Institution-Id": str(institution_id),
            },
            timeout=10,
        )
    except httpx.RequestError:
        return None
    if response.status_code >= 400:
        return None
    return response.json()
