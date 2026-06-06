import pytest
from sqlalchemy.exc import IntegrityError

from app.models.form import Form
from app.models.submission import FormFieldValue
from app.repositories.form_repository import FormRepository


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def form_with_fields(create_form, db_session):
    """A READY form with two fields."""
    form = create_form(institution_id=1, status="READY")
    repo = FormRepository(db_session)
    repo.replace_fields(
        form.id,
        [
            {
                "field_name": "Full Name",
                "field_type": "text",
                "required": True,
                "position": 0,
            },
            {
                "field_name": "Date of Birth",
                "field_type": "date",
                "required": False,
                "position": 1,
            },
        ],
    )
    fields = repo.get_fields(form.id)
    return form, fields


@pytest.fixture
def submitted_form(form_with_fields, db_session):
    """One submission already persisted against form_with_fields."""
    form, fields = form_with_fields
    repo = FormRepository(db_session)
    submission = repo.create_submission(
        form_id=form.id,
        institution_id=1,
        submitter_id="user-42",
        field_values=[
            {
                "field_id": fields[0].id,
                "field_name": fields[0].field_name,
                "value": "Marie Atanga",
            },
            {
                "field_id": fields[1].id,
                "field_name": fields[1].field_name,
                "value": "1990-01-15",
            },
        ],
    )
    return submission, form, fields


# ---------------------------------------------------------------------------
# create_submission
# ---------------------------------------------------------------------------


def test_create_submission_returns_record(form_with_fields, db_session):
    form, fields = form_with_fields
    repo = FormRepository(db_session)
    submission = repo.create_submission(
        form_id=form.id,
        institution_id=1,
        submitter_id="user-42",
        field_values=[
            {
                "field_id": fields[0].id,
                "field_name": fields[0].field_name,
                "value": "Test",
            },
        ],
    )
    assert submission.id is not None
    assert submission.form_id == form.id
    assert submission.institution_id == 1
    assert submission.submitter_id == "user-42"
    assert submission.status == "SUBMITTED"


def test_create_submission_persists_field_values(form_with_fields, db_session):
    form, fields = form_with_fields
    repo = FormRepository(db_session)
    submission = repo.create_submission(
        form_id=form.id,
        institution_id=1,
        submitter_id="user-42",
        field_values=[
            {
                "field_id": fields[0].id,
                "field_name": "Full Name",
                "value": "Marie Atanga",
            },
            {
                "field_id": fields[1].id,
                "field_name": "Date of Birth",
                "value": "1990-01-15",
            },
        ],
    )
    values = (
        db_session.query(FormFieldValue)
        .filter(FormFieldValue.submission_id == submission.id)
        .all()
    )
    assert len(values) == 2
    stored = {v.field_name: v.value for v in values}
    assert stored["Full Name"] == "Marie Atanga"
    assert stored["Date of Birth"] == "1990-01-15"


def test_create_submission_empty_field_values_is_valid(form_with_fields, db_session):
    form, _ = form_with_fields
    repo = FormRepository(db_session)
    submission = repo.create_submission(
        form_id=form.id,
        institution_id=1,
        submitter_id="user-42",
        field_values=[],
    )
    assert submission.id is not None
    assert submission.status == "SUBMITTED"


def test_create_submission_null_value_allowed(form_with_fields, db_session):
    """Optional fields may be submitted with value=None (left blank)."""
    form, fields = form_with_fields
    repo = FormRepository(db_session)
    submission = repo.create_submission(
        form_id=form.id,
        institution_id=1,
        submitter_id="user-42",
        field_values=[
            {"field_id": fields[1].id, "field_name": "Date of Birth", "value": None},
        ],
    )
    fv = (
        db_session.query(FormFieldValue)
        .filter(FormFieldValue.submission_id == submission.id)
        .first()
    )
    assert fv.value is None


def test_create_submission_null_field_id_allowed(form_with_fields, db_session):
    """field_id may be omitted — field_name alone is sufficient."""
    form, _ = form_with_fields
    repo = FormRepository(db_session)
    submission = repo.create_submission(
        form_id=form.id,
        institution_id=1,
        submitter_id="user-42",
        field_values=[{"field_name": "Extra Note", "value": "Hello"}],
    )
    fv = (
        db_session.query(FormFieldValue)
        .filter(FormFieldValue.submission_id == submission.id)
        .first()
    )
    assert fv.field_id is None
    assert fv.value == "Hello"


def test_field_name_survives_schema_replacement(form_with_fields, db_session):
    """field_name is denormalized at submission time; replacing form fields does not alter it."""
    form, fields = form_with_fields
    repo = FormRepository(db_session)
    submission = repo.create_submission(
        form_id=form.id,
        institution_id=1,
        submitter_id="user-42",
        field_values=[
            {"field_id": fields[0].id, "field_name": "Full Name", "value": "Original"},
        ],
    )
    # Simulate admin editing the schema after submission
    repo.replace_fields(
        form.id,
        [
            {
                "field_name": "Renamed Field",
                "field_type": "text",
                "required": False,
                "position": 0,
            }
        ],
    )
    fv = (
        db_session.query(FormFieldValue)
        .filter(FormFieldValue.submission_id == submission.id)
        .first()
    )
    assert fv.field_name == "Full Name"
    assert fv.value == "Original"


# ---------------------------------------------------------------------------
# get_submission
# ---------------------------------------------------------------------------


def test_get_submission_returns_record(submitted_form, db_session):
    submission, _, _ = submitted_form
    repo = FormRepository(db_session)
    fetched = repo.get_submission(submission.id, institution_id=1)
    assert fetched is not None
    assert fetched.id == submission.id


def test_get_submission_wrong_institution_returns_none(submitted_form, db_session):
    submission, _, _ = submitted_form
    repo = FormRepository(db_session)
    assert repo.get_submission(submission.id, institution_id=999) is None


def test_get_submission_nonexistent_returns_none(db_session):
    repo = FormRepository(db_session)
    assert (
        repo.get_submission("00000000-0000-0000-0000-000000000000", institution_id=1)
        is None
    )


# ---------------------------------------------------------------------------
# list_submissions
# ---------------------------------------------------------------------------


def test_list_submissions_returns_all(form_with_fields, db_session):
    form, _ = form_with_fields
    repo = FormRepository(db_session)
    repo.create_submission(
        form_id=form.id, institution_id=1, submitter_id="u1", field_values=[]
    )
    repo.create_submission(
        form_id=form.id, institution_id=1, submitter_id="u2", field_values=[]
    )

    total, items = repo.list_submissions(
        form.id, institution_id=1, page=1, page_size=10
    )
    assert total == 2
    assert len(items) == 2


def test_list_submissions_empty_form_returns_zero(form_with_fields, db_session):
    form, _ = form_with_fields
    repo = FormRepository(db_session)
    total, items = repo.list_submissions(
        form.id, institution_id=1, page=1, page_size=10
    )
    assert total == 0
    assert items == []


def test_list_submissions_scoped_by_institution(db_session, create_form):
    form_a = create_form(institution_id=1)
    form_b = create_form(institution_id=2)
    repo = FormRepository(db_session)
    repo.create_submission(
        form_id=form_a.id, institution_id=1, submitter_id="u1", field_values=[]
    )
    repo.create_submission(
        form_id=form_b.id, institution_id=2, submitter_id="u2", field_values=[]
    )

    total, items = repo.list_submissions(
        form_a.id, institution_id=1, page=1, page_size=10
    )
    assert total == 1
    assert items[0].institution_id == 1


def test_list_submissions_scoped_by_form(form_with_fields, db_session, create_form):
    form1, _ = form_with_fields
    form2 = create_form(institution_id=1)
    repo = FormRepository(db_session)
    repo.create_submission(
        form_id=form1.id, institution_id=1, submitter_id="u1", field_values=[]
    )
    repo.create_submission(
        form_id=form2.id, institution_id=1, submitter_id="u2", field_values=[]
    )

    total, _ = repo.list_submissions(form1.id, institution_id=1, page=1, page_size=10)
    assert total == 1


def test_list_submissions_pagination(form_with_fields, db_session):
    form, _ = form_with_fields
    repo = FormRepository(db_session)
    for i in range(5):
        repo.create_submission(
            form_id=form.id, institution_id=1, submitter_id=f"u{i}", field_values=[]
        )

    _, page1 = repo.list_submissions(form.id, institution_id=1, page=1, page_size=3)
    _, page2 = repo.list_submissions(form.id, institution_id=1, page=2, page_size=3)
    assert len(page1) == 3
    assert len(page2) == 2


def test_list_submissions_ordered_newest_first(form_with_fields, db_session):
    form, _ = form_with_fields
    repo = FormRepository(db_session)
    s1 = repo.create_submission(
        form_id=form.id, institution_id=1, submitter_id="u1", field_values=[]
    )
    s2 = repo.create_submission(
        form_id=form.id, institution_id=1, submitter_id="u2", field_values=[]
    )

    _, items = repo.list_submissions(form.id, institution_id=1, page=1, page_size=10)
    assert items[0].id == s2.id
    assert items[1].id == s1.id


# ---------------------------------------------------------------------------
# FK RESTRICT — deleting a form with submissions must be blocked
# ---------------------------------------------------------------------------


def test_delete_form_blocked_when_submissions_exist(form_with_fields, db_session):
    form, _ = form_with_fields
    repo = FormRepository(db_session)
    repo.create_submission(
        form_id=form.id, institution_id=1, submitter_id="user-42", field_values=[]
    )

    with pytest.raises(IntegrityError):
        repo.delete_form(form)

    db_session.rollback()

    # Form must still exist after the failed delete
    still_there = db_session.query(Form).filter(Form.id == form.id).first()
    assert still_there is not None


def test_delete_form_succeeds_when_no_submissions(form_with_fields, db_session):
    """Control case: delete works fine when no submissions exist."""
    form, _ = form_with_fields
    repo = FormRepository(db_session)
    repo.delete_form(form)

    assert db_session.query(Form).filter(Form.id == form.id).first() is None
