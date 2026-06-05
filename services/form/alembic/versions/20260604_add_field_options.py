"""Add options column to form_fields.

Stores the choice list for select/radio/checkbox-group fields so the end-user
form can render the correct widget. Null for free-text inputs.

Revision ID: 20260604_add_field_options
Revises: 20260604_add_submission_tables
Create Date: 2026-06-04
"""

from alembic import op
import sqlalchemy as sa

revision = "20260604_add_field_options"
down_revision = "20260604_add_submission_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        op.execute("SET search_path TO form_schema")

    op.add_column(
        "form_fields",
        sa.Column("options", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        op.execute("SET search_path TO form_schema")

    op.drop_column("form_fields", "options")
