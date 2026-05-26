from app.services.validation_service import validate_steps


def test_validate_steps_returns_multiple_errors():
    steps = [
        {
            "step_name": "Bad",
            "assigned_role": "nurse",
            "step_order": 2,
            "is_terminal": False,
        }
    ]
    errors = validate_steps(steps)
    assert any("step_order 1" in err for err in errors)
    assert any("terminal" in err for err in errors)
    assert any("Invalid role" in err for err in errors)


def test_validate_steps_duplicate_orders():
    steps = [
        {
            "step_name": "A",
            "assigned_role": "admin",
            "step_order": 1,
            "is_terminal": False,
        },
        {
            "step_name": "B",
            "assigned_role": "staff",
            "step_order": 1,
            "is_terminal": True,
        },
    ]
    errors = validate_steps(steps)
    assert any("Duplicate step_order" in err for err in errors)


def test_validate_steps_ok():
    steps = [
        {
            "step_name": "A",
            "assigned_role": "admin",
            "step_order": 1,
            "is_terminal": False,
        },
        {
            "step_name": "B",
            "assigned_role": "staff",
            "step_order": 2,
            "is_terminal": True,
        },
    ]
    errors = validate_steps(steps)
    assert errors == []
