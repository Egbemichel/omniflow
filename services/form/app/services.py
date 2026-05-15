from sqlalchemy.orm import Session
from typing import List, Optional
from app import models


def create_form(db: Session, name: str, file_path: str, uploaded_by: str) -> models.Form:
    form = models.Form(name=name, file_path=file_path, uploaded_by=uploaded_by)
    db.add(form)
    db.commit()
    db.refresh(form)
    return form


def get_form(db: Session, form_id: str) -> Optional[models.Form]:
    return db.query(models.Form).filter(models.Form.id == form_id).first()


def list_forms(db: Session) -> List[models.Form]:
    return db.query(models.Form).all()


def update_fields(db: Session, form: models.Form, fields: list) -> models.Form:
    form.fields = fields
    form.status = "ready"
    db.commit()
    db.refresh(form)
    return form
