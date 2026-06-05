from app.services.engine import WorkflowEngine


class FakeStep:
    def __init__(self, id, assigned_role, step_order):
        self.id = id
        self.assigned_role = assigned_role
        self.step_order = step_order


class FakeWorkflow:
    def __init__(self, graph=None, steps=None):
        self.graph = graph
        self.steps = steps or []


engine = WorkflowEngine()


# A linear graph: start → entry(Patient) → actor(Nurse) → actor(Doctor) → end
LINEAR_GRAPH = {
    "nodes": [
        {"id": "s", "type": "start"},
        {"id": "e", "type": "entry", "actorType": "Patient"},
        {"id": "a", "type": "actor", "actorType": "Nurse"},
        {"id": "b", "type": "actor", "actorType": "Doctor"},
        {"id": "end", "type": "end"},
    ],
    "edges": [
        {"from": "s", "to": "e"},
        {"from": "e", "to": "a"},
        {"from": "a", "to": "b"},
        {"from": "b", "to": "end"},
    ],
}


def test_graph_start_skips_entry_to_first_actor():
    # The Entry User (submitter) is auto-satisfied; the first task is the actor.
    result = engine.transition(FakeWorkflow(graph=LINEAR_GRAPH), None, "START")
    assert result["next_step_id"] == "a"
    assert result["assigned_role"] == "staff"
    assert result["actor_type"] == "Nurse"
    assert result["status"] == "IN_PROGRESS"


def test_graph_advances_to_next_task():
    result = engine.transition(FakeWorkflow(graph=LINEAR_GRAPH), "a", "APPROVE")
    assert result["next_step_id"] == "b"
    assert result["assigned_role"] == "staff"
    assert result["actor_type"] == "Doctor"


def test_graph_completes_at_end():
    result = engine.transition(FakeWorkflow(graph=LINEAR_GRAPH), "b", "APPROVE")
    assert result["status"] == "COMPLETED"
    assert result["next_step_id"] is None


# A branching graph with a condition: actor(a) → condition(c); Yes → b, No → end
BRANCH_GRAPH = {
    "nodes": [
        {"id": "a", "type": "actor", "actorType": "Reviewer"},
        {"id": "c", "type": "condition"},
        {"id": "b", "type": "actor", "actorType": "Approver"},
        {"id": "end", "type": "end"},
    ],
    "edges": [
        {"from": "a", "to": "c"},
        {"from": "c", "to": "b", "label": "Yes"},
        {"from": "c", "to": "end", "label": "No"},
    ],
}


def test_condition_approve_takes_yes_branch():
    result = engine.transition(FakeWorkflow(graph=BRANCH_GRAPH), "a", "APPROVE")
    assert result["next_step_id"] == "b"
    assert result["actor_type"] == "Approver"


def test_condition_reject_takes_no_branch_to_end():
    result = engine.transition(FakeWorkflow(graph=BRANCH_GRAPH), "a", "REJECT")
    assert result["status"] == "COMPLETED"


# A loop: actor(a) → condition(c); Repeat → back to a, Exit → end
LOOP_GRAPH = {
    "nodes": [
        {"id": "a", "type": "actor", "actorType": "Worker"},
        {"id": "c", "type": "condition"},
        {"id": "end", "type": "end"},
    ],
    "edges": [
        {"from": "a", "to": "c"},
        {"from": "c", "to": "a", "label": "Repeat"},
        {"from": "c", "to": "end", "label": "Exit"},
    ],
}


def test_loop_back_edge_repeats_step():
    # "Repeat" is affirmative → APPROVE loops back to the same actor node.
    result = engine.transition(FakeWorkflow(graph=LOOP_GRAPH), "a", "APPROVE")
    assert result["next_step_id"] == "a"
    assert result["status"] == "IN_PROGRESS"


def test_loop_exit_branch_completes():
    result = engine.transition(FakeWorkflow(graph=LOOP_GRAPH), "a", "REJECT")
    assert result["status"] == "COMPLETED"


def test_falls_back_to_linear_steps_without_graph():
    steps = [FakeStep("st1", "end_user", 1), FakeStep("st2", "staff", 2)]
    workflow = FakeWorkflow(graph=None, steps=steps)
    start = engine.transition(workflow, None, "START")
    assert start["next_step_id"] == "st1"
    nxt = engine.transition(workflow, "st1", "APPROVE")
    assert nxt["next_step_id"] == "st2"
    done = engine.transition(workflow, "st2", "APPROVE")
    assert done["status"] == "COMPLETED"
