from datetime import datetime
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from app.models.workflow import Workflow, WorkflowStep


class WorkflowRepository:
    def __init__(self, session: Session):
        """Repository for workflow persistence and queries."""
        self.session = session

    def create_workflow(
        self,
        workflow_id: str,
        institution_id: int,
        admin_id: int,
        name: str,
        description: str | None,
        form_id: str | None,
    ) -> Workflow:
        workflow = Workflow(
            id=workflow_id,
            institution_id=institution_id,
            admin_id=admin_id,
            name=name,
            description=description,
            form_id=form_id,
            status="DRAFT",
        )
        self.session.add(workflow)
        self.session.commit()
        self.session.refresh(workflow)
        return workflow

    def update_workflow(self, workflow: Workflow, data: dict) -> Workflow:
        for key, value in data.items():
            setattr(workflow, key, value)
        workflow.updated_at = datetime.utcnow()
        self.session.commit()
        self.session.refresh(workflow)
        return workflow

    def get_workflow(self, workflow_id: str, institution_id: int) -> Optional[Workflow]:
        return (
            self.session.query(Workflow)
            .filter(
                Workflow.id == workflow_id, Workflow.institution_id == institution_id
            )
            .first()
        )

    def get_workflow_any(self, workflow_id: str) -> Optional[Workflow]:
        return self.session.query(Workflow).filter(Workflow.id == workflow_id).first()

    def list_workflows(
        self, institution_id: int, page: int, page_size: int
    ) -> Tuple[int, List[Workflow]]:
        query = self.session.query(Workflow).filter(
            Workflow.institution_id == institution_id
        )
        total = query.count()
        items = (
            query.order_by(Workflow.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return total, items

    def add_step(
        self,
        workflow_id: str,
        step_name: str,
        assigned_role: str,
        step_order: int,
        is_terminal: bool,
    ) -> WorkflowStep:
        step = WorkflowStep(
            workflow_id=workflow_id,
            step_name=step_name,
            assigned_role=assigned_role,
            step_order=step_order,
            is_terminal=is_terminal,
        )
        self.session.add(step)
        self.session.commit()
        self.session.refresh(step)
        return step

    def list_steps(self, workflow_id: str) -> List[WorkflowStep]:
        return (
            self.session.query(WorkflowStep)
            .filter(WorkflowStep.workflow_id == workflow_id)
            .order_by(WorkflowStep.step_order.asc())
            .all()
        )

    def get_step(self, step_id: str, workflow_id: str) -> Optional[WorkflowStep]:
        return (
            self.session.query(WorkflowStep)
            .filter(WorkflowStep.id == step_id, WorkflowStep.workflow_id == workflow_id)
            .first()
        )

    def update_step(self, step: WorkflowStep, data: dict) -> WorkflowStep:
        for key, value in data.items():
            setattr(step, key, value)
        step.updated_at = datetime.utcnow()
        self.session.commit()
        self.session.refresh(step)
        return step

    def delete_step(self, step: WorkflowStep) -> None:
        self.session.delete(step)
        self.session.commit()

    def publish(self, workflow: Workflow) -> Workflow:
        workflow.status = "PUBLISHED"
        workflow.locked_at = datetime.utcnow()
        workflow.updated_at = datetime.utcnow()
        self.session.commit()
        self.session.refresh(workflow)
        return workflow
