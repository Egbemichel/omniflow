import os
import redis
import json
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session

from app import models, schemas
from app import workflow_client

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = redis.from_url(REDIS_URL)


def _publish_notification(event_type: str, recipient_id: str, message: str):
    """Publish an event to Redis for the Notification Service."""
    try:
        payload = {
            "event_type": event_type,
            "recipient_id": recipient_id,
            "message": message,
        }
        redis_client.publish("notifications", json.dumps(payload))
    except Exception as e:
        print(f"Failed to publish notification: {e}")


def create_submission(
    db: Session,
    payload: schemas.SubmissionCreate,
    user_id: str,
    institution_id: int,
) -> models.Submission:
    submission = models.Submission(
        workflow_id=payload.workflow_id,
        institution_id=institution_id,
        submitted_by=user_id,
        form_data=payload.form_data,
    )
    db.add(submission)
    db.flush()

    # Call Workflow Service to initialise state
    wf_state = workflow_client.initialise_submission(payload.workflow_id, submission.id)

    submission.current_step_id = wf_state["next_step_id"]

    # Create the first task for the assigned role
    task = models.Task(
        submission_id=submission.id,
        institution_id=institution_id,
        assigned_role=wf_state["assigned_role"],
        status="pending",
    )
    db.add(task)

    # Audit log
    audit = models.AuditEvent(
        submission_id=submission.id,
        institution_id=institution_id,
        action="START",
        actor_id=user_id,
        step_id=wf_state["next_step_id"],
    )
    db.add(audit)

    db.commit()
    db.refresh(submission)

    # Notify staff of new task
    _publish_notification(
        "task_assigned",
        wf_state["assigned_role"],
        f"New submission {submission.id} needs {wf_state['assigned_role']} review.",
    )

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


def get_user_submissions(db: Session, user_id: str) -> List[models.Submission]:
    return (
        db.query(models.Submission)
        .filter(models.Submission.submitted_by == user_id)
        .all()
    )


def get_all_submissions(db: Session) -> List[models.Submission]:
    return db.query(models.Submission).all()


def get_task(db: Session, task_id: str) -> Optional[models.Task]:
    return db.query(models.Task).filter(models.Task.id == task_id).first()


def complete_task(
    db: Session,
    task: models.Task,
    submission: models.Submission,
    actor_id: str,
    action: str,  # APPROVE or REJECT
) -> models.Submission:
    task.status = "completed"
    task.completed_at = datetime.now(timezone.utc)
    task.completed_by = actor_id

    # Get next step from workflow service
    wf_state = workflow_client.advance_submission(
        submission.workflow_id, submission.current_step_id, action
    )

    submission.current_step_id = wf_state["next_step_id"]
    submission.status = wf_state["status"]

    if wf_state["status"] == "IN_PROGRESS":
        new_task = models.Task(
            submission_id=submission.id,
            institution_id=submission.institution_id,
            assigned_role=wf_state["assigned_role"],
            status="pending",
        )
        db.add(new_task)

    # Audit log
    audit = models.AuditEvent(
        submission_id=submission.id,
        institution_id=submission.institution_id,
        action=action,
        actor_id=actor_id,
        step_id=wf_state["next_step_id"],
    )
    db.add(audit)

    db.commit()
    db.refresh(submission)
    return submission


def get_audit_history(db: Session, submission_id: str) -> List[models.AuditEvent]:
    return (
        db.query(models.AuditEvent)
        .filter(models.AuditEvent.submission_id == submission_id)
        .order_by(models.AuditEvent.created_at)
        .all()
    )
