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
    # Set search_path so subsequent operations target auth_schema
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"
    if not is_sqlite:
        op.execute("CREATE SCHEMA IF NOT EXISTS auth_schema")
        op.execute("SET search_path TO auth_schema")

    now_default = sa.text("(CURRENT_TIMESTAMP)") if is_sqlite else sa.text("now()")

    op.create_table(
        "users",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("email", sa.String(), nullable=False, unique=True),
        sa.Column("full_name", sa.String(), nullable=True),
        sa.Column("role", sa.String(), nullable=False, server_default="end_user"),
        sa.Column("institution_id", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("1") if is_sqlite else sa.text("true"),
        ),
        sa.Column("oauth_provider", sa.String(), nullable=True),
        sa.Column("oauth_id", sa.String(), nullable=True),
        sa.Column("last_login", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=now_default,
        ),
        sa.UniqueConstraint("oauth_provider", "oauth_id", name="uq_oauth"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_institution_id", "users", ["institution_id"])


def downgrade() -> None:
    # Set search_path to the target schema for cleanup.
    op.execute("SET search_path TO auth_schema")

    op.drop_index("ix_users_institution_id", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        op.execute("DROP SCHEMA IF EXISTS auth_schema")
