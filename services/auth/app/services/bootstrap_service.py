import os
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.institution import Institution
from app.models.user import User


DEFAULT_BOOTSTRAP_INSTITUTION_ID = 1


def bootstrap_super_admin(db: Session) -> User | None:
    email = os.getenv("BOOTSTRAP_SUPER_ADMIN_EMAIL")
    if not email:
        return None

    normalized_email = email.strip().lower()
    full_name = os.getenv("BOOTSTRAP_SUPER_ADMIN_NAME", "Paper Killer Super Admin")

    institution = db.query(Institution).filter(Institution.id == 1).first()
    if not institution:
        institution = Institution(
            id=DEFAULT_BOOTSTRAP_INSTITUTION_ID,
            name=os.getenv("BOOTSTRAP_INSTITUTION_NAME", "Paper Killer Root"),
            type="office",
        )
        db.add(institution)
        db.flush()

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
