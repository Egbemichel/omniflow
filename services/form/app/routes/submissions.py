import base64
import io
import os

import segno
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.repositories.form_repository import FormRepository
from app.routes.dependencies import require_admin
from app.services import task_client
from app.schemas.form_schema import (
    QRCodeResponse,
    SubmissionListResponse,
    SubmissionResponse,
    SubmitFormRequest,
)

router = APIRouter()


def _domain() -> str:
    return os.getenv("DOMAIN", "localhost")


@router.get("/forms/{form_id}/public-schema")
def get_public_schema(
    form_id: str,
    db: Session = Depends(get_db),
):
    repo = FormRepository(db)
    form = repo.get_form_any(form_id)
    if not form or form.status != "PUBLISHED":
        raise HTTPException(status_code=404, detail="Form not found")
    fields = repo.get_fields(form_id)
    return {
        "form_id": form_id,
        "name": form.original_filename.rsplit(".", 1)[0].replace("_", " ").title(),
        "fields": [
            {
                "id": f.id,
                "field_name": f.field_name,
                "field_type": f.field_type,
                "required": f.required,
                "position": f.position,
                "options": f.options,
            }
            for f in fields
        ],
    }


@router.post(
    "/forms/{form_id}/submit", response_model=SubmissionResponse, status_code=201
)
def submit_form(
    form_id: str,
    payload: SubmitFormRequest,
    db: Session = Depends(get_db),
):
    repo = FormRepository(db)
    form = repo.get_form_any(form_id)
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    if form.status != "PUBLISHED":
        raise HTTPException(status_code=409, detail="Form is not published")

    submission = repo.create_submission(
        form_id=form_id,
        institution_id=form.institution_id,
        submitter_id=payload.submitter_id or "anonymous",
        field_values=[fv.model_dump() for fv in payload.field_values],
    )

    # Best-effort: start the linked workflow in the Task Service. A failure here
    # (no workflow linked, Task Service down) must not fail the form submission.
    form_data = {fv.field_name: fv.value for fv in payload.field_values}
    task_client.start_workflow_submission(
        form_id=form_id,
        institution_id=form.institution_id,
        form_data=form_data,
        submitter_id=submission.submitter_id,
    )

    return {
        "submission_id": submission.id,
        "form_id": form_id,
        "status": submission.status,
    }


@router.get("/forms/{form_id}/submissions", response_model=SubmissionListResponse)
def list_submissions(
    form_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    repo = FormRepository(db)
    institution_id = int(current_user["institution_id"])
    form = repo.get_form(form_id, institution_id)
    if not form:
        other = repo.get_form_any(form_id)
        if other:
            raise HTTPException(status_code=403, detail="Forbidden")
        raise HTTPException(status_code=404, detail="Form not found")

    total, submissions = repo.list_submissions(form_id, institution_id, page, page_size)
    items = [
        {
            "submission_id": s.id,
            "form_id": s.form_id,
            "submitter_id": s.submitter_id,
            "status": s.status,
            "submitted_at": s.submitted_at,
        }
        for s in submissions
    ]
    return {"page": page, "page_size": page_size, "total": total, "items": items}


@router.get("/forms/{form_id}/qr", response_model=QRCodeResponse)
def get_qr_code(
    form_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    repo = FormRepository(db)
    institution_id = int(current_user["institution_id"])
    form = repo.get_form(form_id, institution_id)
    if not form:
        other = repo.get_form_any(form_id)
        if other:
            raise HTTPException(status_code=403, detail="Forbidden")
        raise HTTPException(status_code=404, detail="Form not found")
    if form.status != "PUBLISHED":
        raise HTTPException(
            status_code=409, detail="Form must be PUBLISHED to generate a QR code"
        )

    url = f"https://{_domain()}/submit/{form_id}"
    qr = segno.make(url, error="M")
    buffer = io.BytesIO()
    qr.save(buffer, kind="png", scale=10)
    qr_b64 = base64.b64encode(buffer.getvalue()).decode()

    return {"form_id": form_id, "url": url, "qr_code_base64": qr_b64}
