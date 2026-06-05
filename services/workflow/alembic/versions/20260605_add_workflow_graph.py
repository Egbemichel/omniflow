"""Add graph column to workflows.

Stores the full canvas graph (nodes, edges, linked form, branch labels, back-edges)
authored in the workflow builder. The runtime engine still drives off the flattened
``workflow_steps`` rows; ``graph`` is the authoring source of truth so the builder can
reload and edit the diagram server-side instead of relying on the browser only.

Revision ID: 20260605_add_workflow_graph
Revises: 20260517_create_workflow_tables
Create Date: 2026-06-05
"""

import sqlalchemy as sa
from alembic import op

revision = "20260605_add_workflow_graph"
down_revision = "20260517_create_workflow_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        op.execute("SET search_path TO workflow_schema")

    op.add_column("workflows", sa.Column("graph", sa.JSON(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        op.execute("SET search_path TO workflow_schema")

    op.drop_column("workflows", "graph")
