"""Refactor users table for passwordless auth.
Revision ID: 20260517_refactor_users_table
Revises:
Create Date: 2026-05-17
"""

import sqlalchemy as sa
from alembic import op

revision = "20260517_refactor_users_table"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"
    schema = None if is_sqlite else "auth_schema"

    if not is_sqlite:
        op.execute("CREATE SCHEMA IF NOT EXISTS auth_schema")
        op.execute("SET search_path TO auth_schema")

    op.create_table(
        "users",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("email", sa.String(), nullable=False, unique=True),
        sa.Column("full_name", sa.String(), nullable=True),
        sa.Column("role", sa.String(), nullable=False, server_default="end_user"),
        sa.Column("institution_id", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column("oauth_provider", sa.String(), nullable=True),
        sa.Column("oauth_id", sa.String(), nullable=True),
        sa.Column("last_login", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("oauth_provider", "oauth_id", name="uq_oauth"),
        schema=schema,
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True, schema=schema)
    op.create_index(
        "ix_users_institution_id", "users", ["institution_id"], schema=schema
    )


def downgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"
    schema = None if is_sqlite else "auth_schema"

    if not is_sqlite:
        op.execute("SET search_path TO auth_schema")

    op.drop_index("ix_users_institution_id", table_name="users", schema=schema)
    op.drop_index("ix_users_email", table_name="users", schema=schema)
    op.drop_table("users", schema=schema)

    if not is_sqlite:
        op.execute("DROP SCHEMA IF EXISTS auth_schema")
