"""replace first/last name with full name

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-20 14:10:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("full_name", sa.String(length=200), nullable=False, server_default="")
        )
        batch_op.drop_column("first_name")
        batch_op.drop_column("last_name")

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.alter_column("full_name", server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("last_name", sa.String(length=100), nullable=False, server_default="")
        )
        batch_op.add_column(
            sa.Column("first_name", sa.String(length=100), nullable=False, server_default="")
        )
        batch_op.drop_column("full_name")
