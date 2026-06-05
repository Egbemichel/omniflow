"""Add form_submissions and form_field_values tables.

Revision ID: 20260604_add_submission_tables
Revises: 20260517_create_form_tables
Create Date: 2026-06-04
"""

from alembic import op
import sqlalchemy as sa

revision = "20260604_add_submission_tables"
down_revision = "20260517_create_form_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"
    if not is_sqlite:
        op.execute("SET search_path TO form_schema")

    id_default = None if is_sqlite else sa.text("gen_random_uuid()")
    now_default = sa.text("(CURRENT_TIMESTAMP)") if is_sqlite else sa.text("now()")

    op.create_table(
        "form_submissions",
        sa.Column("id", sa.String(), primary_key=True, server_default=id_default),
        sa.Column(
            "form_id",
            sa.String(),
            sa.ForeignKey("forms.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("institution_id", sa.Integer(), nullable=False),
        sa.Column("submitter_id", sa.String(), nullable=False),
        sa.Column(
            "status", sa.String(), nullable=False, server_default="SUBMITTED"
        ),
        sa.Column(
            "submitted_at", sa.DateTime(timezone=True), server_default=now_default
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=now_default
        ),
    )
    op.create_index(
        "ix_form_submissions_form_id", "form_submissions", ["form_id"]
    )
    op.create_index(
        "ix_form_submissions_institution_id", "form_submissions", ["institution_id"]
    )
    op.create_index(
        "ix_form_submissions_submitter_id", "form_submissions", ["submitter_id"]
    )

    op.create_table(
        "form_field_values",
        sa.Column("id", sa.String(), primary_key=True, server_default=id_default),
        sa.Column(
            "submission_id",
            sa.String(),
            sa.ForeignKey("form_submissions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "field_id",
            sa.String(),
            sa.ForeignKey("form_fields.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("field_name", sa.String(), nullable=False),
        sa.Column("value", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_form_field_values_submission_id", "form_field_values", ["submission_id"]
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        op.execute("SET search_path TO form_schema")

    op.drop_table("form_field_values")
    op.drop_table("form_submissions")
