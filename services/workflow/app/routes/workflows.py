import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.repositories.workflow_repository import WorkflowRepository
from app.routes.dependencies import require_admin
from app.schemas.workflow_schema import (
    WorkflowCreate,
    WorkflowDetailResponse,
    WorkflowListResponse,
    WorkflowUpdate,
)
from app.services.event_service import EventService
from app.services.validation_service import validate_steps

router = APIRouter()


def _get_workflow_or_403(
    repo: WorkflowRepository, workflow_id: str, institution_id: int
):
    workflow = repo.get_workflow(workflow_id, institution_id)
    if workflow:
        return workflow
    other = repo.get_workflow_any(workflow_id)
    if other:
        raise HTTPException(status_code=403, detail="Forbidden")
    raise HTTPException(status_code=404, detail="Workflow not found")


@router.post("/workflows", response_model=WorkflowDetailResponse, status_code=201)
def create_workflow(
    payload: WorkflowCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    repo = WorkflowRepository(db)
    workflow_id = str(uuid.uuid4())

    steps_data = []
    if payload.steps:
        steps_data = [
            {
                "step_name": s.step_name,
                "assigned_role": s.assigned_role.value,
                "step_order": s.step_order,
                "is_terminal": s.is_terminal,
            }
            for s in payload.steps
        ]

    workflow = repo.create_workflow(
        workflow_id=workflow_id,
        institution_id=int(current_user["institution_id"]),
        admin_id=current_user["user_id"],
        name=payload.name,
        description=payload.description,
        form_id=payload.form_id,
        steps=steps_data,
        graph=payload.graph,
    )
    return workflow


@router.patch("/workflows/{workflow_id}", response_model=WorkflowDetailResponse)
def update_workflow(
    workflow_id: str,
    payload: WorkflowUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    repo = WorkflowRepository(db)
    workflow = _get_workflow_or_403(
        repo, workflow_id, int(current_user["institution_id"])
    )
    if workflow.status != "DRAFT":
        raise HTTPException(status_code=409, detail="Workflow is immutable")

    # Step replacement is handled separately from plain column updates.
    column_updates = payload.model_dump(exclude_unset=True, exclude={"steps"})
    if column_updates:
        repo.update_workflow(workflow, column_updates)

    if payload.steps is not None:
        steps_data = [
            {
                "step_name": s.step_name,
                "assigned_role": s.assigned_role.value,
                "step_order": s.step_order,
                "is_terminal": s.is_terminal,
            }
            for s in payload.steps
        ]
        repo.replace_steps(workflow.id, steps_data)
        db.refresh(workflow)

    return workflow


@router.get("/workflows/by-form/{form_id}")
def get_workflow_for_form(form_id: str, db: Session = Depends(get_db)):
    """Resolve the published workflow linked to a form.

    Called server-to-server by the Task Service when a public form submission
    needs to kick off its workflow. No auth — internal, looked up by form id.
    """
    repo = WorkflowRepository(db)
    workflow = repo.get_published_workflow_by_form(form_id)
    if not workflow:
        raise HTTPException(
            status_code=404, detail="No published workflow linked to this form"
        )
    return {"workflow_id": workflow.id, "status": workflow.status}


@router.get("/workflows", response_model=WorkflowListResponse)
def list_workflows(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    repo = WorkflowRepository(db)
    total, items = repo.list_workflows(
        int(current_user["institution_id"]), page, page_size
    )
    payload_items = [
        {
            "workflow_id": wf.id,
            "name": wf.name,
            "description": wf.description,
            "status": wf.status,
            "step_count": len(wf.steps) if wf.steps else 0,
            "created_at": wf.created_at,
            "updated_at": wf.updated_at,
        }
        for wf in items
    ]
    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "items": payload_items,
    }


@router.get("/workflows/{workflow_id}", response_model=WorkflowDetailResponse)
def get_workflow(
    workflow_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    repo = WorkflowRepository(db)
    workflow = _get_workflow_or_403(
        repo, workflow_id, int(current_user["institution_id"])
    )
    return workflow


@router.post("/workflows/{workflow_id}/publish", response_model=WorkflowDetailResponse)
def publish_workflow(
    workflow_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    repo = WorkflowRepository(db)
    workflow = _get_workflow_or_403(
        repo, workflow_id, int(current_user["institution_id"])
    )
    if workflow.status != "DRAFT":
        raise HTTPException(status_code=409, detail="Workflow is immutable")

    steps = repo.list_steps(workflow.id)
    errors = validate_steps(
        [
            {
                "step_name": step.step_name,
                "assigned_role": step.assigned_role,
                "step_order": step.step_order,
                "is_terminal": step.is_terminal,
            }
            for step in steps
        ]
    )
    if errors:
        raise HTTPException(status_code=422, detail={"errors": errors})

    workflow = repo.publish(workflow)

    EventService().publish_workflow_published(
        workflow_id=workflow.id,
        institution_id=workflow.institution_id,
        admin_id=workflow.admin_id,
        step_count=len(steps),
        published_at=workflow.locked_at.isoformat() if workflow.locked_at else "",
    )
    return workflow


@router.post("/workflows/{workflow_id}/submissions")
def trigger_submission(
    workflow_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    repo = WorkflowRepository(db)
    _get_workflow_or_403(repo, workflow_id, int(current_user["institution_id"]))
    raise HTTPException(
        status_code=501,
        detail="Submission trigger coming soon — Task Service will handle this",
    )
