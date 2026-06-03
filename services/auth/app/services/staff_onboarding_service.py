from sqlalchemy.orm import Session

from app.models.staff_onboarding import StaffCSVRow
from app.models.user import User


ROLE_ALIASES = {
    "base_user": "end_user",
    "end_user": "end_user",
    "user": "end_user",
    "workflow_actor": "staff",
    "staff": "staff",
    "institution_admin": "admin",
    "admin": "admin",
    "super_admin": "super_admin",
}


def normalize_role(role: str | None) -> str:
    if not role:
        return "end_user"
    key = role.strip().lower()
    return ROLE_ALIASES.get(key, key)


def find_staff_row_for_email(db: Session, email: str) -> StaffCSVRow | None:
    return (
        db.query(StaffCSVRow)
        .filter(StaffCSVRow.email == email.strip().lower())
        .order_by(StaffCSVRow.created_at.desc(), StaffCSVRow.id.desc())
        .first()
    )


def apply_staff_csv_match(db: Session, user: User) -> User:
    """Apply the latest matching staff CSV row to a login user, if one exists."""
    row = find_staff_row_for_email(db, user.email)
    if not row:
        return user

    user.institution_id = row.institution_id
    user.role = normalize_role(row.role)
    user.full_name = row.name or user.full_name
    row.matched_user_id = user.id
    db.commit()
    db.refresh(user)
    return user
