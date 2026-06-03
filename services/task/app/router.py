from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from app import schemas, services
from app.database import get_db

router = APIRouter()


def _require_auth(
    x_user_id: Optional[str] = Header(None),
    x_user_role: Optional[str] = Header(None),
    x_institution_id: Optional[str] = Header(None),
):
    if not x_user_id or not x_user_role:
        raise HTTPException(status_code=401, detail="Authentication required")
    return {
        "user_id": x_user_id,
        "role": x_user_role,
        "institution_id": int(x_institution_id) if x_institution_id else 1,
    }


# ── Submissions ──────────────────────────────────────────────────────────────


@router.post("/submissions", response_model=schemas.SubmissionOut, status_code=201)
def create_submission(
    payload: schemas.SubmissionCreate,
    db: Session = Depends(get_db),
    auth: dict = Depends(_require_auth),
):
    return services.create_submission(
        db, payload, auth["user_id"], auth["institution_id"]
    )


@router.get("/submissions", response_model=List[schemas.SubmissionStatusOut])
def get_submissions(
    db: Session = Depends(get_db),
    auth: dict = Depends(_require_auth),
):
    if auth["role"] in ["staff", "admin", "institution_admin", "super_admin"]:
        return services.get_all_submissions(db)
    return services.get_user_submissions(db, auth["user_id"])


@router.get(
    "/submissions/{submission_id}/status", response_model=schemas.SubmissionStatusOut
)
def get_submission_status(
    submission_id: str,
    db: Session = Depends(get_db),
    auth: dict = Depends(_require_auth),
):
    sub = services.get_submission(db, submission_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")
    # Only the submitter or staff/admin can view
    if auth["role"] == "end_user" and sub.submitted_by != auth["user_id"]:
        raise HTTPException(status_code=403, detail="Forbidden")
    return schemas.SubmissionStatusOut(
        id=sub.id, status=sub.status, current_step_id=sub.current_step_id
    )


@router.get(
    "/submissions/{submission_id}/history", response_model=List[schemas.AuditEventOut]
)
def get_submission_history(
    submission_id: str,
    db: Session = Depends(get_db),
    auth: dict = Depends(_require_auth),
):
    sub = services.get_submission(db, submission_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")
    return services.get_audit_history(db, submission_id)


# ── Tasks ────────────────────────────────────────────────────────────────────


@router.get("/tasks/inbox", response_model=List[schemas.TaskOut])
def get_inbox(
    db: Session = Depends(get_db),
    auth: dict = Depends(_require_auth),
):
    return services.get_inbox(db, auth["role"])


class TaskActionRequest(BaseModel):
    action: str  # APPROVE, REJECT


@router.post("/tasks/{task_id}/complete")
def complete_task(
    task_id: str,
    payload: TaskActionRequest,
    db: Session = Depends(get_db),
    auth: dict = Depends(_require_auth),
):
    task = services.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status == "completed":
        raise HTTPException(status_code=409, detail="Task already completed")

    if task.assigned_role != auth["role"] and auth["role"] not in [
        "admin",
        "super_admin",
    ]:
        raise HTTPException(
            status_code=403, detail="Your role cannot complete this task"
        )

    submission = services.get_submission(db, task.submission_id)
    return services.complete_task(db, task, submission, auth["user_id"], payload.action)

    sub = services.get_submission(db, task.submission_id)
    return services.complete_task(db, task, sub, auth["user_id"], auth["role"])
