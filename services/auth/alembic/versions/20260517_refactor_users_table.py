"""Refactor users table for passwordless auth.

Revision ID: 20260517_refactor_users_table
Revises:
Create Date: 2026-05-17
"""

from alembic import op
import sqlalchemy as sa

revision = "20260517_refactor_users_table"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("institution_id", sa.Integer(), nullable=False, server_default="1"))
        batch_op.add_column(sa.Column("oauth_provider", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("oauth_id", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("last_login", sa.DateTime(timezone=True), nullable=True))
        batch_op.create_unique_constraint("uq_oauth", ["oauth_provider", "oauth_id"])
        batch_op.drop_column("hashed_password")


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("hashed_password", sa.String(), nullable=True))
        batch_op.drop_constraint("uq_oauth", type_="unique")
        batch_op.drop_column("last_login")
        batch_op.drop_column("oauth_id")
        batch_op.drop_column("oauth_provider")
        batch_op.drop_column("institution_id")
