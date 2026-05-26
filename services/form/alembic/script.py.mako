"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    # IMPORTANT: Ensure search_path is set to form_schema for PostgreSQL migrations
    # to prevent CI collisions and isolate microservice data.
    op.execute("SET search_path TO form_schema")
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    op.execute("SET search_path TO form_schema")
    ${downgrades if downgrades else "pass"}
