"""Add actor_types registry.

An institution-defined actor label (e.g. "Triage Nurse") mapped to a system role.
Previously actor types were only implied by staff CSV rows and always mapped to
``staff``; this table lets admins register them explicitly against any system role.

Revision ID: 20260605_actor_types
Revises: 20260604_add_user_actor_type
Create Date: 2026-06-05
"""

import sqlalchemy as sa
from alembic import op

revision = "20260605_actor_types"
down_revision = "20260604_user_actor_type"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"
    if not is_sqlite:
        op.execute("SET search_path TO auth_schema")

    now_default = sa.text("(CURRENT_TIMESTAMP)") if is_sqlite else sa.text("now()")

    op.create_table(
        "actor_types",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("institution_id", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column("system_role", sa.String(), nullable=False, server_default="staff"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now_default),
        sa.UniqueConstraint("institution_id", "label", name="uq_actor_type_label"),
    )
    op.create_index(
        "ix_actor_types_institution_id", "actor_types", ["institution_id"]
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        op.execute("SET search_path TO auth_schema")

    op.drop_index("ix_actor_types_institution_id", table_name="actor_types")
    op.drop_table("actor_types")
