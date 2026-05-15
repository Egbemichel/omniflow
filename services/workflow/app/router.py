from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import Optional

from app import schemas, services
from app.database import get_db

router = APIRouter()


def _require_admin(x_user_role: Optional[str] = Header(None)):
    if x_user_role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")


def _get_role(x_user_role: Optional[str] = Header(None)) -> str:
    if not x_user_role:
        raise HTTPException(status_code=401, detail="Authentication required")
    return x_user_role


# ── Workflow CRUD ─────────────────────────────────────────────────────────────

@router.post("/workflows", response_model=schemas.WorkflowOut, status_code=201)
def create_workflow(
    payload: schemas.WorkflowCreate,
    db: Session = Depends(get_db),
    _: None = Depends(_require_admin),
):
    return services.create_workflow(db, payload)


@router.get("/workflows/{workflow_id}", response_model=schemas.WorkflowOut)
def get_workflow(workflow_id: str, db: Session = Depends(get_db), role: str = Depends(_get_role)):
    wf = services.get_workflow(db, workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return wf


@router.post("/workflows/{workflow_id}/publish", response_model=schemas.WorkflowOut)
def publish_workflow(
    workflow_id: str,
    db: Session = Depends(get_db),
    _: None = Depends(_require_admin),
):
    wf = services.get_workflow(db, workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if wf.status == "published":
        raise HTTPException(status_code=409, detail="Workflow is already published")
    return services.publish_workflow(db, wf)


@router.post("/workflows/{workflow_id}/steps", response_model=schemas.StepOut, status_code=201)
def add_step(
    workflow_id: str,
    payload: schemas.StepIn,
    db: Session = Depends(get_db),
    _: None = Depends(_require_admin),
):
    wf = services.get_workflow(db, workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if wf.status == "published":
        raise HTTPException(status_code=409, detail="Cannot edit a published workflow")
    return services.add_step(db, wf, payload)


# ── State machine ─────────────────────────────────────────────────────────────

@router.post("/workflows/{workflow_id}/initialise", status_code=201)
def initialise(
    workflow_id: str,
    payload: schemas.InitialiseRequest,
    db: Session = Depends(get_db),
    _: None = Depends(_require_admin),
):
    wf = services.get_workflow(db, workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if wf.status != "published":
        raise HTTPException(status_code=409, detail="Workflow must be published to initialise")
    state = services.initialise_submission(db, wf, payload.submission_id)
    return services.build_state_response(state, wf)


@router.post("/workflows/{workflow_id}/transition")
def transition(
    workflow_id: str,
    payload: schemas.TransitionRequest,
    db: Session = Depends(get_db),
    x_user_role: Optional[str] = Header(None),
):
    if not x_user_role:
        raise HTTPException(status_code=401, detail="Authentication required")

    wf = services.get_workflow(db, workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")

    state = services.get_submission_state(db, payload.submission_id)
    if not state:
        raise HTTPException(status_code=404, detail="Submission not found")

    if state.status == "completed":
        raise HTTPException(status_code=409, detail="Submission is already completed")

    # Verify role matches the current step's assigned role
    current_role = services.build_state_response(state, wf)["assigned_role"]
    if x_user_role != current_role and x_user_role != "admin":
        raise HTTPException(status_code=403, detail="Your role cannot advance this step")

    state = services.advance_submission(db, state, wf)
    return services.build_state_response(state, wf)
