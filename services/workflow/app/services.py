from typing import Optional
from sqlalchemy.orm import Session

from app import models, schemas


# ── Workflow CRUD ────────────────────────────────────────────────────────────

def create_workflow(db: Session, payload: schemas.WorkflowCreate) -> models.Workflow:
    workflow = models.Workflow(name=payload.name, description=payload.description)
    db.add(workflow)
    db.flush()  # get the ID before adding steps
    for step_data in payload.steps:
        step = models.WorkflowStep(
            workflow_id=workflow.id,
            order=step_data.order,
            name=step_data.name,
            assigned_role=step_data.assigned_role,
        )
        db.add(step)
    db.commit()
    db.refresh(workflow)
    return workflow


def get_workflow(db: Session, workflow_id: str) -> Optional[models.Workflow]:
    return db.query(models.Workflow).filter(models.Workflow.id == workflow_id).first()


def publish_workflow(db: Session, workflow: models.Workflow) -> models.Workflow:
    workflow.status = "published"
    db.commit()
    db.refresh(workflow)
    return workflow


def add_step(db: Session, workflow: models.Workflow, step_data: schemas.StepIn) -> models.WorkflowStep:
    step = models.WorkflowStep(
        workflow_id=workflow.id,
        order=step_data.order,
        name=step_data.name,
        assigned_role=step_data.assigned_role,
    )
    db.add(step)
    db.commit()
    db.refresh(step)
    return step


# ── State machine ────────────────────────────────────────────────────────────

def _get_step_for_order(workflow: models.Workflow, order: int) -> Optional[models.WorkflowStep]:
    for step in workflow.steps:
        if step.order == order:
            return step
    return None


def _role_for_step(workflow: models.Workflow, step_order: int) -> Optional[str]:
    step = _get_step_for_order(workflow, step_order)
    return step.assigned_role if step else None


def initialise_submission(
    db: Session, workflow: models.Workflow, submission_id: str
) -> models.SubmissionState:
    first_step = min(workflow.steps, key=lambda s: s.order)
    state = models.SubmissionState(
        submission_id=submission_id,
        workflow_id=workflow.id,
        current_step=first_step.order,
        status="in_progress",
    )
    db.add(state)
    db.commit()
    db.refresh(state)
    return state


def get_submission_state(db: Session, submission_id: str) -> Optional[models.SubmissionState]:
    return (
        db.query(models.SubmissionState)
        .filter(models.SubmissionState.submission_id == submission_id)
        .first()
    )


def advance_submission(
    db: Session, state: models.SubmissionState, workflow: models.Workflow
) -> models.SubmissionState:
    """Move submission to next step, or mark completed if no more steps."""
    sorted_steps = sorted(workflow.steps, key=lambda s: s.order)
    current_orders = [s.order for s in sorted_steps]
    current_index = current_orders.index(state.current_step)

    if current_index + 1 < len(sorted_steps):
        state.current_step = sorted_steps[current_index + 1].order
    else:
        state.current_step = None
        state.status = "completed"

    db.commit()
    db.refresh(state)
    return state


def build_state_response(
    state: models.SubmissionState, workflow: models.Workflow
) -> dict:
    assigned_role = None
    if state.current_step is not None:
        assigned_role = _role_for_step(workflow, state.current_step)
    return {
        "submission_id": state.submission_id,
        "workflow_id": state.workflow_id,
        "current_step": state.current_step,
        "status": state.status,
        "assigned_role": assigned_role,
    }
