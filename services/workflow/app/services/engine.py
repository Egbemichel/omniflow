from typing import Any, Dict, List, Optional

from app.models.workflow import Workflow

# Graph node types that pause the flow and create a task someone must complete.
# The Entry User node is NOT one of these: it represents the submitter, whose
# action (submitting the form) is what started the workflow — so the engine
# passes through it to the first actor step rather than assigning it as a task.
TASK_TYPES = {"actor"}

# Branch-label vocabularies used to resolve a condition node from a task action.
AFFIRMATIVE = {
    "yes", "y", "if", "true", "approve", "approved", "continue", "repeat", "done", "ok",
}
NEGATIVE = {"no", "n", "else", "false", "reject", "rejected", "exit", "stop"}


class WorkflowEngine:
    """Decides the next state of a submission.

    Two modes:
    - **Graph mode** (preferred): walks ``workflow.graph`` — the canvas authored in
      the builder — honoring conditional branches, jumps, and loops (back-edges).
    - **Linear mode** (fallback): for workflows with no graph, follows the flattened
      ``workflow.steps`` by ``step_order`` (the original behavior).
    """

    def transition(
        self, workflow: Workflow, current_step_id: Optional[str], action: str
    ) -> Dict[str, Any]:
        graph = getattr(workflow, "graph", None)
        if isinstance(graph, dict) and graph.get("nodes"):
            return self._graph_transition(graph, current_step_id, action)
        return self._linear_transition(workflow, current_step_id, action)

    # ── Graph mode ───────────────────────────────────────────────────────────
    def _graph_transition(
        self, graph: Dict[str, Any], current_node_id: Optional[str], action: str
    ) -> Dict[str, Any]:
        node_list = [n for n in graph.get("nodes", []) if n.get("id")]
        nodes = {n["id"]: n for n in node_list}
        edges = graph.get("edges", [])

        def out_edges(nid: str) -> List[dict]:
            return [e for e in edges if e.get("from") == nid]

        # Determine where to start walking from.
        if current_node_id is None:
            start = next((n for n in node_list if n.get("type") == "start"), None)
            if start is None:
                first = next((n for n in node_list if n.get("type") in TASK_TYPES), None)
                if first is None:
                    return {"status": "ERROR", "message": "Workflow has no start or task node"}
                return self._as_step(first)
            cursor = start["id"]
        elif current_node_id in nodes:
            cursor = current_node_id
        else:
            return {"status": "ERROR", "message": "Current step not found in graph"}

        # Walk forward to the next task node (stop) or an end node (complete).
        # Conditions are resolved by the action; a visited set bounds degenerate
        # condition-only cycles. Reaching a task node — even via a back-edge —
        # stops the walk, which is exactly how a loop "repeats" a step.
        visited_conditions: set = set()
        while True:
            node = nodes.get(cursor)
            if node is None:
                return {"status": "ERROR", "message": "Dangling node reference"}

            outs = out_edges(cursor)
            if not outs:
                # End node, or a task with no successor — treat as completion.
                return {"next_step_id": None, "status": "COMPLETED", "assigned_role": None}

            if node.get("type") == "condition":
                if cursor in visited_conditions:
                    return {"status": "ERROR", "message": "Condition cycle has no task node"}
                visited_conditions.add(cursor)
                edge = self._pick_branch(outs, action)
            else:
                edge = outs[0]

            nxt = nodes.get(edge.get("to"))
            if nxt is None:
                return {"status": "ERROR", "message": "Arrow points to a missing node"}
            if nxt.get("type") in TASK_TYPES:
                return self._as_step(nxt)
            if nxt.get("type") == "end":
                return {"next_step_id": None, "status": "COMPLETED", "assigned_role": None}
            cursor = nxt["id"]  # start or condition — keep walking

    def _pick_branch(self, outs: List[dict], action: Optional[str]) -> dict:
        labeled = [(e, str(e.get("label") or "").strip().lower()) for e in outs]
        is_negative = bool(action) and action.upper() in {"REJECT", "NO", "DENY", "FALSE"}
        if is_negative:
            for edge, label in labeled:
                if label in NEGATIVE:
                    return edge
            return outs[1] if len(outs) > 1 else outs[0]
        # Affirmative / START / unknown → take the affirmative branch, else first.
        for edge, label in labeled:
            if label in AFFIRMATIVE:
                return edge
        return outs[0]

    def _as_step(self, node: dict) -> Dict[str, Any]:
        return {
            "next_step_id": node["id"],
            "status": "IN_PROGRESS",
            "assigned_role": "end_user" if node.get("type") == "entry" else "staff",
            "actor_type": node.get("actorType") or None,
        }

    # ── Linear mode (legacy fallback) ────────────────────────────────────────
    def _linear_transition(
        self, workflow: Workflow, current_step_id: Optional[str], action: str
    ) -> Dict[str, Any]:
        steps = sorted(workflow.steps, key=lambda s: s.step_order)

        if not steps:
            return {"status": "ERROR", "message": "No steps in workflow"}

        if current_step_id is None:
            return {
                "next_step_id": steps[0].id,
                "status": "IN_PROGRESS",
                "assigned_role": steps[0].assigned_role,
                "actor_type": None,
            }

        current_step = next((s for s in steps if s.id == current_step_id), None)
        if not current_step:
            return {"status": "ERROR", "message": "Current step not found"}

        if action == "REJECT":
            return {
                "next_step_id": steps[0].id,
                "status": "IN_PROGRESS",
                "assigned_role": steps[0].assigned_role,
                "actor_type": None,
                "message": "Returned to start",
            }

        current_index = next(
            (idx for idx, s in enumerate(steps) if s.id == current_step_id), -1
        )

        if current_index + 1 < len(steps):
            next_step = steps[current_index + 1]
            return {
                "next_step_id": next_step.id,
                "status": "IN_PROGRESS",
                "assigned_role": next_step.assigned_role,
                "actor_type": None,
            }
        return {"next_step_id": None, "status": "COMPLETED", "assigned_role": None}
