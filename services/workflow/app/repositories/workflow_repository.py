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
        admin_id: str,
        name: str,
        description: str | None,
        form_id: str | None,
        steps: List[dict] | None = None,
        graph: dict | None = None,
    ) -> Workflow:
        workflow = Workflow(
            id=workflow_id,
            institution_id=institution_id,
            admin_id=admin_id,
            name=name,
            description=description,
            form_id=form_id,
            status="DRAFT",
            graph=graph,
        )
        self.session.add(workflow)

        if steps:
            for s_data in steps:
                step = WorkflowStep(
                    workflow_id=workflow_id,
                    step_name=s_data["step_name"],
                    assigned_role=s_data["assigned_role"],
                    step_order=s_data["step_order"],
                    is_terminal=s_data.get("is_terminal", False),
                )
                self.session.add(step)

        self.session.commit()
        self.session.refresh(workflow)
        return workflow

    def replace_steps(self, workflow_id: str, steps: List[dict]) -> None:
        """Delete a workflow's existing steps and insert the supplied set.

        Used when the builder re-saves an edited graph so the flattened step
        list stays in sync with the canvas.
        """
        self.session.query(WorkflowStep).filter(
            WorkflowStep.workflow_id == workflow_id
        ).delete(synchronize_session=False)
        for s_data in steps:
            self.session.add(
                WorkflowStep(
                    workflow_id=workflow_id,
                    step_name=s_data["step_name"],
                    assigned_role=s_data["assigned_role"],
                    step_order=s_data["step_order"],
                    is_terminal=s_data.get("is_terminal", False),
                )
            )
        self.session.commit()

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

    def get_published_workflow_by_form(self, form_id: str) -> Optional[Workflow]:
        """The most recently published workflow linked to a form (or None)."""
        return (
            self.session.query(Workflow)
            .filter(Workflow.form_id == form_id, Workflow.status == "PUBLISHED")
            .order_by(Workflow.locked_at.desc(), Workflow.updated_at.desc())
            .first()
        )

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
