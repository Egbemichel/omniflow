import pytest
from app.routes.onboarding import _parse_staff_csv
from fastapi import HTTPException

def test_parse_csv_success():
    csv_data = "name,email,role,department\nJohn Doe,john@test.com,staff,IT\n"
    rows, fieldnames = _parse_staff_csv(csv_data)
    assert len(rows) == 1
    assert rows[0]["email"] == "john@test.com"

def test_parse_csv_missing_columns():
    csv_data = "name,email\nJohn Doe,john@test.com\n"
    with pytest.raises(HTTPException) as exc:
        _parse_staff_csv(csv_data)
    assert exc.value.status_code == 400
    assert "missing required columns" in exc.value.detail

def test_parse_csv_blank_fields():
    csv_data = "name,email,role,department\nJohn Doe,john@test.com,staff,\n"
    with pytest.raises(HTTPException) as exc:
        _parse_staff_csv(csv_data)
    assert exc.value.status_code == 400
    assert "blank required fields" in exc.value.detail

def test_parse_csv_duplicate_email():
    csv_data = "name,email,role,department\nJohn,j@a.com,s,it\nJane,j@a.com,s,it\n"
    with pytest.raises(HTTPException) as exc:
        _parse_staff_csv(csv_data)
    assert exc.value.status_code == 400
    assert "duplicate email" in exc.value.detail
