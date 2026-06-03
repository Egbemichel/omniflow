from app.models.institution import Institution
from app.models.user import User
from app.services.bootstrap_service import bootstrap_super_admin


def test_bootstrap_super_admin_creates_root_user_and_institution(
    db_session, monkeypatch
):
    monkeypatch.setenv("BOOTSTRAP_SUPER_ADMIN_EMAIL", "root@pk.local")
    monkeypatch.setenv("BOOTSTRAP_SUPER_ADMIN_NAME", "Root Admin")
    monkeypatch.setenv("BOOTSTRAP_INSTITUTION_NAME", "Root Institution")

    user = bootstrap_super_admin(db_session)

    assert user is not None
    assert user.email == "root@pk.local"
    assert user.role == "super_admin"
    assert user.institution_id == 1
    assert user.oauth_provider == "bootstrap"

    institution = db_session.query(Institution).filter(Institution.id == 1).first()
    assert institution is not None
    assert institution.name == "Root Institution"


def test_bootstrap_super_admin_is_idempotent_and_repairs_existing_user(
    db_session, monkeypatch
):
    monkeypatch.setenv("BOOTSTRAP_SUPER_ADMIN_EMAIL", "root@pk.local")
    user = User(
        email="root@pk.local",
        full_name="Existing",
        role="end_user",
        institution_id=99,
        oauth_provider="magic_link",
        oauth_id="root@pk.local",
        is_active=False,
    )
    db_session.add(user)
    db_session.commit()

    bootstrapped = bootstrap_super_admin(db_session)
    bootstrapped_again = bootstrap_super_admin(db_session)

    assert bootstrapped.id == user.id
    assert bootstrapped_again.id == user.id
    assert bootstrapped.role == "super_admin"
    assert bootstrapped.institution_id == 1
    assert bootstrapped.is_active is True
    assert db_session.query(User).filter(User.email == "root@pk.local").count() == 1
