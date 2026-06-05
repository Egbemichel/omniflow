from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.actor_type import ActorType
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


def resolve_role_and_actor_type(
    label: str | None,
    db: Session | None = None,
    institution_id: int | None = None,
) -> tuple[str, str | None]:
    """Map a CSV role_label to a (system_role, actor_type) pair.

    Resolution order:
    1. A registered actor type (institution's `actor_types` table) wins — it may
       map to any system role (e.g. "Registrar" -> role="admin").
    2. A known system-role keyword (admin, staff, end_user, super_admin, aliases)
       sets that system role with no actor type.
    3. Any other label is a custom actor type defaulting to the ``staff`` system
       role, with the original label preserved (e.g. "NURSE" -> staff, "NURSE").
    """
    if not label or not label.strip():
        return "end_user", None
    clean = label.strip()
    key = clean.lower()

    if db is not None and institution_id is not None:
        match = (
            db.query(ActorType)
            .filter(
                ActorType.institution_id == institution_id,
                func.lower(ActorType.label) == key,
            )
            .first()
        )
        if match:
            return match.system_role, clean

    if key in ROLE_ALIASES:
        return ROLE_ALIASES[key], None
    return "staff", clean


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
    user.role, user.actor_type = resolve_role_and_actor_type(
        row.role, db=db, institution_id=row.institution_id
    )
    user.full_name = row.name or user.full_name
    row.matched_user_id = user.id
    db.commit()
    db.refresh(user)
    return user
