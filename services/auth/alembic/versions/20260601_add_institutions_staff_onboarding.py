"""Add institutions and staff CSV onboarding tables.

Revision ID: 20260601_staff_onboarding
Revises: 20260517_refactor_users_table
Create Date: 2026-06-01
"""

import sqlalchemy as sa
from alembic import op

revision = "20260601_staff_onboarding"
down_revision = "20260517_refactor_users_table"
branch_labels = None
depends_on = None


def _now_default(is_sqlite: bool):
    return sa.text("(CURRENT_TIMESTAMP)") if is_sqlite else sa.text("now()")


def upgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"
    if not is_sqlite:
        op.execute("CREATE SCHEMA IF NOT EXISTS auth_schema")
        op.execute("SET search_path TO auth_schema")

    now_default = _now_default(is_sqlite)

    op.create_table(
        "institutions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(), nullable=False, unique=True),
        sa.Column("type", sa.String(), nullable=False, server_default="other"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now_default),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now_default),
    )

    op.create_table(
        "staff_csv_uploads",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("institution_id", sa.Integer(), nullable=False),
        sa.Column("uploaded_by", sa.String(), nullable=False),
        sa.Column("file_name", sa.String(), nullable=False),
        sa.Column("raw_content", sa.String(), nullable=True),
        sa.Column("parsed_rows", sa.JSON(), nullable=True),
        sa.Column("row_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "upload_status", sa.String(), nullable=False, server_default="pending"
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now_default),
    )
    op.create_index(
        "ix_staff_csv_uploads_institution_id",
        "staff_csv_uploads",
        ["institution_id"],
    )

    op.create_table(
        "staff_csv_rows",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("upload_id", sa.String(), nullable=False),
        sa.Column("institution_id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("department", sa.String(), nullable=True),
        sa.Column("extra_fields", sa.JSON(), nullable=True),
        sa.Column("matched_user_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now_default),
        sa.ForeignKeyConstraint(
            ["upload_id"],
            ["staff_csv_uploads.id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_staff_csv_rows_upload_id", "staff_csv_rows", ["upload_id"])
    op.create_index(
        "ix_staff_csv_rows_institution_id",
        "staff_csv_rows",
        ["institution_id"],
    )
    op.create_index("ix_staff_csv_rows_email", "staff_csv_rows", ["email"])


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        op.execute("SET search_path TO auth_schema")

    op.drop_index("ix_staff_csv_rows_email", table_name="staff_csv_rows")
    op.drop_index("ix_staff_csv_rows_institution_id", table_name="staff_csv_rows")
    op.drop_index("ix_staff_csv_rows_upload_id", table_name="staff_csv_rows")
    op.drop_table("staff_csv_rows")

    op.drop_index(
        "ix_staff_csv_uploads_institution_id",
        table_name="staff_csv_uploads",
    )
    op.drop_table("staff_csv_uploads")
    op.drop_table("institutions")
