"""Create workflow tables.

Revision ID: 20260517_create_workflow_tables
Revises:
Create Date: 2026-05-17
"""

from alembic import op
import sqlalchemy as sa

revision = "20260517_create_workflow_tables"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"
    schema = None if is_sqlite else "workflow"

    if not is_sqlite:
        op.execute("CREATE SCHEMA IF NOT EXISTS workflow")

    id_default = None if is_sqlite else sa.text("gen_random_uuid()")
    now_default = None if is_sqlite else sa.text("now()")

    op.create_table(
        "workflows",
        sa.Column("id", sa.String(), primary_key=True, server_default=id_default),
        sa.Column("institution_id", sa.Integer(), nullable=False),
        sa.Column("admin_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("form_id", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="DRAFT"),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now_default),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now_default),
        schema=schema,
    )

    op.create_table(
        "workflow_steps",
        sa.Column("id", sa.String(), primary_key=True, server_default=id_default),
        sa.Column(
            "workflow_id",
            sa.String(),
            sa.ForeignKey(
                "workflow.workflows.id" if not is_sqlite else "workflows.id",
                ondelete="CASCADE",
            ),
            nullable=False,
        ),
        sa.Column("step_name", sa.String(), nullable=False),
        sa.Column("assigned_role", sa.String(), nullable=False),
        sa.Column("step_order", sa.Integer(), nullable=False),
        sa.Column("is_terminal", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now_default),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now_default),
        schema=schema,
    )


def downgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"
    schema = None if is_sqlite else "workflow"

    op.drop_table("workflow_steps", schema=schema)
    op.drop_table("workflows", schema=schema)
    if not is_sqlite:
        op.execute("DROP SCHEMA IF EXISTS workflow")
