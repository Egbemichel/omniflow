import os

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
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

    repo.replace_fields(form_id, [field.model_dump() for field in payload.fields])
    repo.update_status(form, "CONFIRMED")

    fields = repo.get_fields(form_id)
    return {"form_id": form.id, "status": form.status, "fields": fields}

@router.delete("/forms/{form_id}", status_code=204)
def delete_form(
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

    # Delete the file from disk if it exists
    if form.file_path and os.path.exists(form.file_path):
        try:
            os.remove(form.file_path)
        except OSError:
            pass

    repo.delete_form(form)
    return None


@router.get("/forms/{form_id}/file")
def get_form_file(
    form_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    """Serve the originally uploaded file so the admin can preview it.

    Institution-scoped; the file is streamed inline with its stored mime type.
    """
    repo = FormRepository(db)
    institution_id = int(current_user["institution_id"])
    form = repo.get_form(form_id, institution_id)
    if not form:
        other = repo.get_form_any(form_id)
        if other:
            raise HTTPException(status_code=403, detail="Forbidden")
        raise HTTPException(status_code=404, detail="Form not found")
    if not form.file_path or not os.path.exists(form.file_path):
        raise HTTPException(status_code=404, detail="Uploaded file not found")

    return FileResponse(
        form.file_path,
        media_type=form.mime_type or "application/octet-stream",
        content_disposition_type="inline",
    )

@router.post("/forms/{form_id}/publish", response_model=FormStatusResponse)
def publish_form(
    form_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    repo = FormRepository(db)
    institution_id = int(current_user["institution_id"])
    form = repo.get_form(form_id, institution_id)
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")

    # Store fields in json_definition for the engine
    fields = repo.get_fields(form_id)
    json_def = {
        "fields": [
            {"name": f.field_name, "type": f.field_type, "required": f.required}
            for f in fields
        ]
    }
    repo.update_json_definition(form, json_def)
    repo.publish_form(form)

    return {
        "form_id": form.id,
        "status": form.status,
        "field_count": len(fields),
        "fields": fields,
    }


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
    if form.status not in {"READY", "CONFIRMED"}:
        raise HTTPException(
            status_code=409,
            detail="Form must be READY or CONFIRMED before a workflow can be suggested",
        )

    fields = repo.get_fields(form_id)
    field_names = [f.field_name.lower() for f in fields]

    # Keyword maps to roles
    role_keywords = {
        "nurse": ["nurse", "triage", "vital", "temperature", "blood pressure", "weight", "height"],
        "doctor": ["doctor", "physician", "diagnosis", "prescription", "medical", "treatment", "clinical"],
        "pharmacist": ["pharmacist", "medication", "drug", "dosage", "pharmacy"],
        "admin": ["admin", "signature", "approval", "authorisation", "authorization", "sign off", "director"],
    }

    # Find which roles are relevant based on field names
    matched_roles = []
    for role, keywords in role_keywords.items():
        for field_name in field_names:
            if any(keyword in field_name for keyword in keywords):
                if role not in matched_roles:
                    matched_roles.append(role)
                break

    # Always end with admin sign-off if not already there
    if not matched_roles:
        matched_roles = ["staff", "admin"]
    elif "admin" not in matched_roles:
        matched_roles.append("admin")

    # Build suggested steps
    suggested_steps = [
        {
            "order": idx + 1,
            "name": f"{role.capitalize()} Review",
            "assigned_role": role,
        }
        for idx, role in enumerate(matched_roles)
    ]

    return {
        "form_id": form_id,
        "suggested_workflow_name": f"{form.original_filename.rsplit('.', 1)[0].replace('_', ' ').title()} Workflow",
        "steps": suggested_steps,
        "note": "This is a suggestion based on field names. Review and adjust before creating the workflow.",
    }
