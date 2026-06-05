"""Add actor_type to tasks.

Tasks are routed to a staff inbox by the graph's actor type (e.g. "Triage Nurse"),
not the broad `staff` system role. ``actor_type`` is populated from the Workflow
Service transition response.

Revision ID: 20260605_task_actor_type
Revises: 953eda04b1f4
Create Date: 2026-06-05
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260605_task_actor_type"
down_revision: Union[str, None] = "953eda04b1f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "sqlite":
        conn.execute(sa.text("SET search_path TO task_schema"))

    op.add_column("tasks", sa.Column("actor_type", sa.String(), nullable=True))
    op.create_index(op.f("ix_tasks_actor_type"), "tasks", ["actor_type"], unique=False)


def downgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "sqlite":
        conn.execute(sa.text("SET search_path TO task_schema"))

    op.drop_index(op.f("ix_tasks_actor_type"), table_name="tasks")
    op.drop_column("tasks", "actor_type")
