from app.routes.dependencies import (
    require_admin,
    require_super_admin,
    require_institution_admin,
)
from fastapi import HTTPException
import pytest


class MockUser:
    def __init__(self, role):
        self.role = role


def test_require_admin_ok():
    for role in ["super_admin", "institution_admin", "admin"]:
        user = MockUser(role)
        assert require_admin(user) == user


def test_require_admin_fail():
    user = MockUser("end_user")
    with pytest.raises(HTTPException) as exc:
        require_admin(user)
    assert exc.value.status_code == 403


def test_require_super_admin_ok():
    user = MockUser("super_admin")
    assert require_super_admin(user) == user


def test_require_super_admin_fail():
    for role in ["admin", "institution_admin", "end_user"]:
        user = MockUser(role)
        with pytest.raises(HTTPException) as exc:
            require_super_admin(user)
        assert exc.value.status_code == 403


def test_require_institution_admin_ok():
    for role in ["super_admin", "institution_admin"]:
        user = MockUser(role)
        assert require_institution_admin(user) == user


def test_require_institution_admin_fail():
    for role in ["admin", "end_user"]:
        user = MockUser(role)
        with pytest.raises(HTTPException) as exc:
            require_institution_admin(user)
        assert exc.value.status_code == 403
