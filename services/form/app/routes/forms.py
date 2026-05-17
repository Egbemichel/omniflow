from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.repositories.form_repository import FormRepository
from app.routes.dependencies import require_admin
from app.schemas.form_schema import (
    FormListResponse,
    FormSchemaResponse,
    FormSchemaUpdateRequest,
    FormStatusResponse,
)

router = APIRouter()


@router.get("/forms", response_model=FormListResponse)
def list_forms(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    repo = FormRepository(db)
    total, forms = repo.list_forms(int(current_user["institution_id"]), page, page_size)
    items = [
        {
            "form_id": form.id,
            "original_filename": form.original_filename,
            "status": form.status,
            "created_at": form.created_at,
            "updated_at": form.updated_at,
        }
        for form in forms
    ]
    return {"page": page, "page_size": page_size, "total": total, "items": items}


@router.get("/forms/{form_id}/status", response_model=FormStatusResponse)
def get_status(
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

    fields = []
    if form.status in {"READY", "CONFIRMED"}:
        fields = repo.get_fields(form_id)

    return {
        "form_id": form.id,
        "status": form.status,
        "field_count": len(fields),
        "fields": fields or None,
    }


@router.get("/forms/{form_id}/schema", response_model=FormSchemaResponse)
def get_schema(
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

    fields = repo.get_fields(form_id) if form.status in {"READY", "CONFIRMED"} else []
    return {"form_id": form.id, "status": form.status, "fields": fields}


@router.patch("/forms/{form_id}/schema", response_model=FormSchemaResponse)
def update_schema(
    form_id: str,
    payload: FormSchemaUpdateRequest,
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
    if form.status == "CONFIRMED":
        raise HTTPException(status_code=409, detail="Form already confirmed")
    if form.status != "READY":
        raise HTTPException(status_code=409, detail="Form not ready")

    repo.replace_fields(form_id, [field.model_dump() for field in payload.fields])
    repo.update_status(form, "CONFIRMED")

    fields = repo.get_fields(form_id)
    return {"form_id": form.id, "status": form.status, "fields": fields}


@router.get("/forms/{form_id}/suggest-workflow")
def suggest_workflow(
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
    raise HTTPException(status_code=501, detail="Workflow suggestion coming soon")
