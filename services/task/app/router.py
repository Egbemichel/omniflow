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
    x_actor_type: Optional[str] = Header(None),
):
    if not x_user_id or not x_user_role:
        raise HTTPException(status_code=401, detail="Authentication required")
    return {
        "user_id": x_user_id,
        "role": x_user_role,
        "institution_id": int(x_institution_id) if x_institution_id else 1,
        "actor_type": x_actor_type,
    }


# ── Submissions ──────────────────────────────────────────────────────────────


@router.post("/submissions", response_model=schemas.SubmissionOut, status_code=201)
def create_submission(
    payload: schemas.SubmissionCreate,
    db: Session = Depends(get_db),
    auth: dict = Depends(_require_auth),
):
    submitter = payload.submitter_id or auth["user_id"]
    try:
        return services.create_submission(
            db, payload, submitter, auth["institution_id"]
        )
    except services.NoWorkflowError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


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
        id=sub.id,
        status=sub.status,
        current_step_id=sub.current_step_id,
        form_id=sub.form_id,
        form_data=sub.form_data or {},
    )


@router.patch(
    "/submissions/{submission_id}/form-data",
    response_model=schemas.SubmissionStatusOut,
)
def update_submission_form_data(
    submission_id: str,
    payload: schemas.FormDataUpdate,
    db: Session = Depends(get_db),
    auth: dict = Depends(_require_auth),
):
    # Only staff/admin may edit the submitted form — end users are read-only.
    if auth["role"] not in ("staff", "admin", "institution_admin", "super_admin"):
        raise HTTPException(status_code=403, detail="Only staff can edit a submission")
    sub = services.get_submission(db, submission_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")
    sub = services.update_form_data(db, sub, payload.form_data, auth["user_id"])
    return schemas.SubmissionStatusOut(
        id=sub.id,
        status=sub.status,
        current_step_id=sub.current_step_id,
        form_id=sub.form_id,
        form_data=sub.form_data or {},
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
    return services.get_inbox(
        db, auth["role"], auth["institution_id"], auth.get("actor_type")
    )


class TaskActionRequest(BaseModel):
    action: str = "APPROVE"  # APPROVE, REJECT


def _can_complete(task, auth: dict) -> bool:
    if auth["role"] in ("admin", "super_admin"):
        return True
    # A task with an actor type is matched on actor type (case-insensitive);
    # otherwise on role.
    if task.actor_type:
        return (auth.get("actor_type") or "").lower() == task.actor_type.lower()
    return task.assigned_role == auth["role"]


@router.post("/tasks/{task_id}/complete")
def complete_task(
    task_id: str,
    payload: Optional[TaskActionRequest] = None,
    db: Session = Depends(get_db),
    auth: dict = Depends(_require_auth),
):
    task = services.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status == "completed":
        raise HTTPException(status_code=409, detail="Task already completed")

    if not _can_complete(task, auth):
        raise HTTPException(
            status_code=403, detail="Your role cannot complete this task"
        )

    action = (payload or TaskActionRequest()).action
    submission = services.get_submission(db, task.submission_id)
    return services.complete_task(db, task, submission, auth["user_id"], action)
