from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session

from app import models, schemas
from app import workflow_client


def create_submission(
    db: Session,
    payload: schemas.SubmissionCreate,
    user_id: str,
) -> models.Submission:
    submission = models.Submission(
        workflow_id=payload.workflow_id,
        submitted_by=user_id,
        form_data=payload.form_data,
    )
    db.add(submission)
    db.flush()

    # Call Workflow Service to initialise state
    wf_state = workflow_client.initialise_submission(payload.workflow_id, submission.id)

    # Create the first task for the assigned role
    task = models.Task(
        submission_id=submission.id,
        assigned_role=wf_state["assigned_role"],
        status="pending",
    )
    db.add(task)
    db.commit()
    db.refresh(submission)
    return submission


def get_submission(db: Session, submission_id: str) -> Optional[models.Submission]:
    return (
        db.query(models.Submission)
        .filter(models.Submission.id == submission_id)
        .first()
    )


def get_inbox(db: Session, role: str) -> List[models.Task]:
    return (
        db.query(models.Task)
        .filter(models.Task.assigned_role == role, models.Task.status == "pending")
        .all()
    )


def get_task(db: Session, task_id: str) -> Optional[models.Task]:
    return db.query(models.Task).filter(models.Task.id == task_id).first()


def complete_task(
    db: Session,
    task: models.Task,
    submission: models.Submission,
    actor_id: str,
    actor_role: str,
) -> models.Task:
    task.status = "completed"
    task.completed_by = actor_id
    task.completed_at = datetime.now(timezone.utc)
    db.flush()

    # Record audit event
    event = models.AuditEvent(
        submission_id=submission.id,
        action="task_completed",
        actor_id=actor_id,
        actor_role=actor_role,
    )
    db.add(event)

    # Advance workflow state
    wf_state = workflow_client.advance_submission(
        submission.workflow_id, submission.id, actor_role
    )

    if wf_state["status"] == "completed":
        submission.status = "completed"
    else:
        # Create next task
        next_task = models.Task(
            submission_id=submission.id,
            assigned_role=wf_state["assigned_role"],
            status="pending",
        )
        db.add(next_task)

    db.commit()
    db.refresh(task)
    return task


def get_audit_history(db: Session, submission_id: str) -> List[models.AuditEvent]:
    return (
        db.query(models.AuditEvent)
        .filter(models.AuditEvent.submission_id == submission_id)
        .order_by(models.AuditEvent.created_at)
        .all()
    )
