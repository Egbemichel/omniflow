from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.repositories.workflow_repository import WorkflowRepository
from app.routes.dependencies import require_admin
from app.schemas.workflow_schema import StepCreate, StepOut, StepUpdate

router = APIRouter()


def _get_workflow_or_403(repo: WorkflowRepository, workflow_id: str, institution_id: int):
    workflow = repo.get_workflow(workflow_id, institution_id)
    if workflow:
        return workflow
    other = repo.get_workflow_any(workflow_id)
    if other:
        raise HTTPException(status_code=403, detail="Forbidden")
    raise HTTPException(status_code=404, detail="Workflow not found")


@router.post("/workflows/{workflow_id}/steps", response_model=StepOut, status_code=201)
def add_step(
    workflow_id: str,
    payload: StepCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    repo = WorkflowRepository(db)
    workflow = _get_workflow_or_403(repo, workflow_id, int(current_user["institution_id"]))
    if workflow.status != "DRAFT":
        raise HTTPException(status_code=409, detail="Workflow is immutable")
    return repo.add_step(
        workflow_id=workflow.id,
        step_name=payload.step_name,
        assigned_role=payload.assigned_role.value,
        step_order=payload.step_order,
        is_terminal=payload.is_terminal,
    )


@router.get("/workflows/{workflow_id}/steps", response_model=list[StepOut])
def list_steps(
    workflow_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    repo = WorkflowRepository(db)
    workflow = _get_workflow_or_403(repo, workflow_id, int(current_user["institution_id"]))
    return repo.list_steps(workflow.id)


@router.patch("/workflows/{workflow_id}/steps/{step_id}", response_model=StepOut)
def update_step(
    workflow_id: str,
    step_id: str,
    payload: StepUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    repo = WorkflowRepository(db)
    workflow = _get_workflow_or_403(repo, workflow_id, int(current_user["institution_id"]))
    if workflow.status != "DRAFT":
        raise HTTPException(status_code=409, detail="Workflow is immutable")
    step = repo.get_step(step_id, workflow.id)
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")

    updates = payload.model_dump(exclude_unset=True)
    if "assigned_role" in updates and updates["assigned_role"] is not None:
        updates["assigned_role"] = updates["assigned_role"].value
    return repo.update_step(step, updates)


@router.delete("/workflows/{workflow_id}/steps/{step_id}")
def delete_step(
    workflow_id: str,
    step_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    repo = WorkflowRepository(db)
    workflow = _get_workflow_or_403(repo, workflow_id, int(current_user["institution_id"]))
    if workflow.status != "DRAFT":
        raise HTTPException(status_code=409, detail="Workflow is immutable")
    step = repo.get_step(step_id, workflow.id)
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")
    repo.delete_step(step)
    return {"status": "deleted"}
