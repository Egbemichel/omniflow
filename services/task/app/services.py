import os
import redis
import json
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import func
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


class NoWorkflowError(Exception):
    """No published workflow could be resolved for the submission."""


def create_submission(
    db: Session,
    payload: schemas.SubmissionCreate,
    user_id: str,
    institution_id: int,
) -> models.Submission:
    # A public form submission supplies form_id; resolve it to a published workflow.
    workflow_id = payload.workflow_id
    if not workflow_id and payload.form_id:
        workflow_id = workflow_client.find_workflow_for_form(payload.form_id)
    if not workflow_id:
        raise NoWorkflowError("No published workflow linked to this form")

    submission = models.Submission(
        workflow_id=workflow_id,
        form_id=payload.form_id,
        institution_id=institution_id,
        submitted_by=user_id,
        form_data=payload.form_data,
    )
    db.add(submission)
    db.flush()

    # Call Workflow Service to initialise state
    wf_state = workflow_client.initialise_submission(workflow_id, submission.id)

    submission.current_step_id = wf_state.get("next_step_id")

    # Create the first task, routed by actor type when the workflow defines one.
    routing = wf_state.get("actor_type") or wf_state.get("assigned_role")
    task = models.Task(
        submission_id=submission.id,
        institution_id=institution_id,
        assigned_role=wf_state.get("assigned_role"),
        actor_type=wf_state.get("actor_type"),
        status="pending",
    )
    db.add(task)

    # Audit log
    audit = models.AuditEvent(
        submission_id=submission.id,
        institution_id=institution_id,
        action="submission_created",
        actor_id=user_id,
        step_id=wf_state.get("next_step_id"),
    )
    db.add(audit)

    db.commit()
    db.refresh(submission)

    # Notify the relevant staff of the new task.
    _publish_notification(
        "task_assigned",
        routing,
        f"New submission {submission.id} needs {routing} review.",
    )

    return submission


def get_submission(db: Session, submission_id: str) -> Optional[models.Submission]:
    return (
        db.query(models.Submission)
        .filter(models.Submission.id == submission_id)
        .first()
    )


def get_inbox(
    db: Session,
    role: str,
    institution_id: int,
    actor_type: Optional[str] = None,
) -> List[models.Task]:
    """Pending tasks for the requester, scoped to their institution.

    A staff member with an actor type sees only tasks for that actor type;
    otherwise tasks are matched on the broad system role (legacy workflows).
    """
    query = db.query(models.Task).filter(
        models.Task.status == "pending",
        models.Task.institution_id == institution_id,
    )
    if actor_type:
        # Actor-type labels are matched case-insensitively — the CSV/registry and
        # the workflow graph may differ in casing (e.g. "Nurse" vs "NURSE").
        query = query.filter(func.lower(models.Task.actor_type) == actor_type.lower())
    else:
        query = query.filter(models.Task.assigned_role == role)
    return query.all()


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


def update_form_data(
    db: Session,
    submission: models.Submission,
    form_data: dict,
    actor_id: str,
) -> models.Submission:
    """Replace a submission's form data (staff edit) and record it in the audit log."""
    submission.form_data = form_data
    db.add(
        models.AuditEvent(
            submission_id=submission.id,
            institution_id=submission.institution_id,
            action="form_edited",
            actor_id=actor_id,
            step_id=submission.current_step_id,
        )
    )
    db.commit()
    db.refresh(submission)
    return submission


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

    # Ask the Workflow Service where the submission goes next. The engine walks
    # the graph (conditions/loops/jumps) using the action to resolve branches.
    wf_state = workflow_client.advance_submission(
        submission.workflow_id, submission.current_step_id, action
    )

    submission.current_step_id = wf_state.get("next_step_id")
    completed = wf_state.get("status") == "COMPLETED"
    submission.status = "completed" if completed else "in_progress"

    if not completed and wf_state.get("assigned_role"):
        db.add(
            models.Task(
                submission_id=submission.id,
                institution_id=submission.institution_id,
                assigned_role=wf_state.get("assigned_role"),
                actor_type=wf_state.get("actor_type"),
                status="pending",
            )
        )

    # Append-only audit log.
    audit = models.AuditEvent(
        submission_id=submission.id,
        institution_id=submission.institution_id,
        action="task_completed",
        actor_id=actor_id,
        step_id=wf_state.get("next_step_id"),
    )
    db.add(audit)

    db.commit()
    db.refresh(submission)

    if completed:
        _publish_notification(
            "workflow_completed",
            submission.submitted_by,
            f"Your submission {submission.id} has completed.",
        )
    elif wf_state.get("actor_type") or wf_state.get("assigned_role"):
        routing = wf_state.get("actor_type") or wf_state.get("assigned_role")
        _publish_notification(
            "task_assigned",
            routing,
            f"Submission {submission.id} needs {routing} review.",
        )

    return submission


def get_audit_history(db: Session, submission_id: str) -> List[models.AuditEvent]:
    # Newest first.
    return (
        db.query(models.AuditEvent)
        .filter(models.AuditEvent.submission_id == submission_id)
        .order_by(models.AuditEvent.created_at.desc())
        .all()
    )
