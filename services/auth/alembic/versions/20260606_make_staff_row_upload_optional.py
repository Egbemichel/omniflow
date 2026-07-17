"""Make staff CSV row upload reference optional.

Revision ID: 20260606_make_staff_row_upload_optional
Revises: 20260605_add_actor_types
Create Date: 2026-07-17
"""

import sqlalchemy as sa
from alembic import op

revision = "20260606_make_staff_row_upload_optional"
down_revision = "20260605_actor_types"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        op.execute("SET search_path TO auth_schema")
        op.alter_column(
            "staff_csv_rows",
            "upload_id",
            existing_type=sa.String(),
            nullable=True,
        )
        return

    with op.batch_alter_table("staff_csv_rows") as batch_op:
        batch_op.alter_column("upload_id", existing_type=sa.String(), nullable=True)


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        op.execute("SET search_path TO auth_schema")
        op.alter_column(
            "staff_csv_rows",
            "upload_id",
            existing_type=sa.String(),
            nullable=False,
        )
        return

    with op.batch_alter_table("staff_csv_rows") as batch_op:
        batch_op.alter_column("upload_id", existing_type=sa.String(), nullable=False)
