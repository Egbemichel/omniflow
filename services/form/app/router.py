from fastapi import APIRouter, Depends, HTTPException, Header, UploadFile, File
from sqlalchemy.orm import Session
from typing import Optional, List
import os
import shutil
import uuid

from app import schemas, services
from app.database import get_db

router = APIRouter()
UPLOAD_DIR = "/tmp/form_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _require_admin(x_user_role: Optional[str] = Header(None)):
    if x_user_role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")


@router.post("/forms", response_model=schemas.FormOut, status_code=201)
async def upload_form(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    x_user_id: Optional[str] = Header(None),
    _: None = Depends(_require_admin),
):
    file_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}_{file.filename}")
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return services.create_form(
        db, file.filename or "unnamed", file_path, x_user_id or "unknown"
    )


@router.get("/forms", response_model=List[schemas.FormOut])
def list_forms(
    db: Session = Depends(get_db), x_user_role: Optional[str] = Header(None)
):
    if not x_user_role:
        raise HTTPException(status_code=401, detail="Authentication required")
    return services.list_forms(db)


@router.get("/forms/{form_id}", response_model=schemas.FormOut)
def get_form(
    form_id: str,
    db: Session = Depends(get_db),
    x_user_role: Optional[str] = Header(None),
):
    if not x_user_role:
        raise HTTPException(status_code=401, detail="Authentication required")
    form = services.get_form(db, form_id)
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    return form


@router.patch("/forms/{form_id}/fields", response_model=schemas.FormOut)
def update_fields(
    form_id: str,
    payload: schemas.FieldUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(_require_admin),
):
    form = services.get_form(db, form_id)
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    return services.update_fields(db, form, payload.fields)
