import os
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.institution import Institution
from app.models.user import User


DEFAULT_BOOTSTRAP_INSTITUTION_ID = 1


def _sync_institution_sequence(db: Session) -> None:
    if db.bind is None or db.bind.dialect.name != "postgresql":
        return

    schema = os.getenv("DATABASE_SCHEMA", "auth_schema")

    sql = (
        "SELECT setval("
        f"pg_get_serial_sequence('{schema}.institutions', 'id'), "
        f"GREATEST((SELECT COALESCE(MAX(id), 1) FROM {schema}.institutions), 1), "
        "true)"
    )

    db.execute(text(sql))
    db.commit()


def ensure_default_institution(db: Session) -> Institution:
    desired_name = os.getenv("BOOTSTRAP_INSTITUTION_NAME", "Paper Killer Root")
    desired_type = os.getenv("BOOTSTRAP_INSTITUTION_TYPE", "office")

    institution = db.query(Institution).filter(Institution.id == 1).first()
    if institution:
        changed = False
        if institution.name != desired_name:
            institution.name = desired_name
            changed = True
        if institution.type != desired_type:
            institution.type = desired_type
            changed = True
        if changed:
            db.commit()
            db.refresh(institution)
        _sync_institution_sequence(db)
        return institution

    institution = Institution(
        id=DEFAULT_BOOTSTRAP_INSTITUTION_ID,
        name=desired_name,
        type=desired_type,
    )
    db.add(institution)
    db.commit()
    db.refresh(institution)
    _sync_institution_sequence(db)
    return institution


def bootstrap_super_admin(db: Session) -> User | None:
    email = os.getenv("BOOTSTRAP_SUPER_ADMIN_EMAIL")
    if not email:
        return None

    normalized_email = email.strip().lower()
    full_name = os.getenv("BOOTSTRAP_SUPER_ADMIN_NAME", "Paper Killer Super Admin")

    institution = ensure_default_institution(db)

    user = db.query(User).filter(User.email == normalized_email).first()
    if user:
        changed = False
        if user.role != "super_admin":
            user.role = "super_admin"
            changed = True
        if user.institution_id != institution.id:
            user.institution_id = institution.id
            changed = True
        if not user.is_active:
            user.is_active = True
            changed = True
        if changed:
            db.commit()
            db.refresh(user)
        return user

    user = User(
        email=normalized_email,
        full_name=full_name,
        role="super_admin",
        institution_id=institution.id,
        is_active=True,
        oauth_provider="bootstrap",
        oauth_id=normalized_email,
        last_login=datetime.utcnow(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
