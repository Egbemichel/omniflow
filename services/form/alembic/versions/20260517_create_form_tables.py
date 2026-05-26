"""Create form tables.

Revision ID: 20260517_create_form_tables
Revises:
Create Date: 2026-05-17
"""

from alembic import op
import sqlalchemy as sa

revision = "20260517_create_form_tables"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Explicitly set search_path for PostgreSQL to ensure tables are created in the correct schema.
    # This prevents CI collisions and isolates microservice data.
    op.execute("SET search_path TO form_schema")

    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"
    schema = None if is_sqlite else "form_schema"

    if not is_sqlite:
        op.execute("CREATE SCHEMA IF NOT EXISTS form_schema")

    id_default = None if is_sqlite else sa.text("gen_random_uuid()")
    now_default = None if is_sqlite else sa.text("now()")

    op.create_table(
        "forms",
        sa.Column("id", sa.String(), primary_key=True, server_default=id_default),
        sa.Column("institution_id", sa.Integer(), nullable=False),
        sa.Column("admin_id", sa.Integer(), nullable=False),
        sa.Column("original_filename", sa.String(), nullable=False),
        sa.Column("file_path", sa.String(), nullable=False),
        sa.Column("mime_type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="UPLOADED"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now_default),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now_default),
        schema=schema,
    )

    op.create_table(
        "form_fields",
        sa.Column("id", sa.String(), primary_key=True, server_default=id_default),
        sa.Column(
            "form_id",
            sa.String(),
            sa.ForeignKey(
                "form_schema.forms.id" if not is_sqlite else "forms.id",
                ondelete="CASCADE",
            ),
            nullable=False,
        ),
        sa.Column("field_name", sa.String(), nullable=False),
        sa.Column("field_type", sa.String(), nullable=False, server_default="text"),
        sa.Column(
            "required", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now_default),
        schema=schema,
    )


def downgrade() -> None:
    # Set search_path to the target schema for cleanup.
    op.execute("SET search_path TO form_schema")

    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"
    schema = None if is_sqlite else "form_schema"

    op.drop_table("form_fields", schema=schema)
    op.drop_table("forms", schema=schema)
    if not is_sqlite:
        op.execute("DROP SCHEMA IF EXISTS form_schema")
