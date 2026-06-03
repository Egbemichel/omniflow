from typing import Optional, Dict, Any
from app.models.workflow import Workflow


class WorkflowEngine:
    def transition(
        self, workflow: Workflow, current_step_id: Optional[str], action: str
    ) -> Dict[str, Any]:
        """
        Determines the next state of a submission.
        If yaml_definition exists, it uses that. Otherwise, it follows numeric step_order.
        """
        steps = sorted(workflow.steps, key=lambda s: s.step_order)

        if not steps:
            return {"status": "ERROR", "message": "No steps in workflow"}

        if current_step_id is None:
            # Start of workflow
            return {
                "next_step_id": steps[0].id,
                "status": "IN_PROGRESS",
                "assigned_role": steps[0].assigned_role,
            }

        current_step = next((s for s in steps if s.id == current_step_id), None)
        if not current_step:
            return {"status": "ERROR", "message": "Current step not found"}

        if action == "REJECT":
            # For now, rejection sends it back to the first step or cancels
            # Simple policy: return to step 0
            return {
                "next_step_id": steps[0].id,
                "status": "IN_PROGRESS",
                "assigned_role": steps[0].assigned_role,
                "message": "Returned to start",
            }

        # Find next step in order
        current_index = -1
        for idx, s in enumerate(steps):
            if s.id == current_step_id:
                current_index = idx
                break

        if current_index + 1 < len(steps):
            next_step = steps[current_index + 1]
            return {
                "next_step_id": next_step.id,
                "status": "IN_PROGRESS",
                "assigned_role": next_step.assigned_role,
            }
        else:
            # Terminal step
            return {"next_step_id": None, "status": "COMPLETED", "assigned_role": None}
