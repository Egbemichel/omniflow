from typing import Iterable, List

ALLOWED_ROLES = {"admin", "staff", "end_user"}


def validate_steps(steps: Iterable[dict]) -> List[str]:
    errors: List[str] = []
    steps_list = list(steps)
    if len(steps_list) == 0:
        errors.append("Workflow must have at least one step")
        return errors

    step_orders = [step.get("step_order") for step in steps_list]
    if 1 not in step_orders:
        errors.append("Workflow must have a step with step_order 1 (start step)")

    terminal_steps = [step for step in steps_list if step.get("is_terminal") is True]
    if len(terminal_steps) != 1:
        errors.append("Workflow must have exactly one terminal step")

    duplicates = {order for order in step_orders if step_orders.count(order) > 1}
    if duplicates:
        ordered = ", ".join(str(value) for value in sorted(duplicates))
        errors.append(f"Duplicate step_order values are not allowed: {ordered}")

    for step in steps_list:
        role = step.get("assigned_role")
        if role not in ALLOWED_ROLES:
            name = step.get("step_name", "")
            errors.append(
                f"Invalid role '{role}' on step '{name}' — must be one of admin, staff, end_user"
            )

    return errors
