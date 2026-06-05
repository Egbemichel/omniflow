"""Add actor_type column to users.

A user's system role (admin / staff / end_user) and their actor type are two
distinct layers. Custom staff actor types (e.g. "NURSE", "Triage Nurse") all map
to the ``staff`` system role; the specific label now lives in ``actor_type``
instead of being stored as the system role.

Revision ID: 20260604_user_actor_type
Revises: 20260601_staff_onboarding
Create Date: 2026-06-04
"""

import sqlalchemy as sa
from alembic import op

revision = "20260604_user_actor_type"
down_revision = "20260601_staff_onboarding"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        op.execute("SET search_path TO auth_schema")

    op.add_column("users", sa.Column("actor_type", sa.String(), nullable=True))

    # Backfill: any role that is not a known system role is a leaked actor type
    # (the old code stored custom CSV labels like "nurse" in the role column).
    # Move it to actor_type and set the system role to "staff".
    op.execute(
        """
        UPDATE users
        SET actor_type = role,
            role = 'staff'
        WHERE role NOT IN (
            'end_user', 'staff', 'admin', 'institution_admin', 'super_admin'
        )
        """
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        op.execute("SET search_path TO auth_schema")

    op.drop_column("users", "actor_type")
