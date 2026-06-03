from datetime import datetime
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from app.models.form import Form, FormField


class FormRepository:
    def __init__(self, session: Session):
        """Repository for form persistence and queries."""
        self.session = session

    def create_form(
        self,
        form_id: str,
        institution_id: int,
        admin_id: int,
        original_filename: str,
        file_path: str,
        mime_type: str,
        status: str,
    ) -> Form:
        form = Form(
            id=form_id,
            institution_id=institution_id,
            admin_id=admin_id,
            original_filename=original_filename,
            file_path=file_path,
            mime_type=mime_type,
            status=status,
        )
        self.session.add(form)
        self.session.commit()
        self.session.refresh(form)
        return form

    def get_form(self, form_id: str, institution_id: int) -> Optional[Form]:
        return (
            self.session.query(Form)
            .filter(Form.id == form_id, Form.institution_id == institution_id)
            .first()
        )

    def get_form_any(self, form_id: str) -> Optional[Form]:
        return self.session.query(Form).filter(Form.id == form_id).first()

    def list_forms(
        self, institution_id: int, page: int, page_size: int
    ) -> Tuple[int, List[Form]]:
        query = self.session.query(Form).filter(Form.institution_id == institution_id)
        total = query.count()
        items = (
            query.order_by(Form.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return total, items

    def update_status(self, form: Form, status: str) -> Form:
        form.status = status
        form.updated_at = datetime.utcnow()
        self.session.commit()
        self.session.refresh(form)
        return form

    def replace_fields(self, form_id: str, fields: List[dict]) -> int:
        self.session.query(FormField).filter(FormField.form_id == form_id).delete()
        new_fields = [
            FormField(
                form_id=form_id,
                field_name=field["field_name"],
                field_type=field.get("field_type", "text"),
                required=field.get("required", False),
                position=field.get("position", 0),
            )
            for field in fields
        ]
        self.session.add_all(new_fields)
        self.session.commit()
        return len(new_fields)

    def get_fields(self, form_id: str) -> List[FormField]:
        return (
            self.session.query(FormField)
            .filter(FormField.form_id == form_id)
            .order_by(FormField.position.asc())
            .all()
        )
    def delete_form(self, form: Form) -> None:
        self.session.query(FormField).filter(FormField.form_id == form.id).delete()
        self.session.delete(form)
        self.session.commit()
