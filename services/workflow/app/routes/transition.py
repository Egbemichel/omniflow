from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.repositories.workflow_repository import WorkflowRepository
from app.services.engine import WorkflowEngine
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/workflows", tags=["Transitions"])


class TransitionRequest(BaseModel):
    current_step_id: Optional[str] = None
    action: str  # START, APPROVE, REJECT


class TransitionResponse(BaseModel):
    next_step_id: Optional[str]
    status: str
    assigned_role: Optional[str]
    actor_type: Optional[str] = None
    message: Optional[str] = None


@router.post("/{workflow_id}/transition", response_model=TransitionResponse)
def transition_workflow(
    workflow_id: str, request: TransitionRequest, db: Session = Depends(get_db)
):
    repo = WorkflowRepository(db)
    # The Task Service calls this without institution context; look up by id only.
    workflow = repo.get_workflow_any(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    engine = WorkflowEngine()
    result = engine.transition(workflow, request.current_step_id, request.action)

    if result.get("status") == "ERROR":
        raise HTTPException(status_code=400, detail=result.get("message"))

    return result
