"""add is_super_admin to employees

Revision ID: b2d3f4h5j6l7
Revises: a1c2e3g4i5k6
Create Date: 2026-03-24 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b2d3f4h5j6l7"
down_revision: Union[str, None] = "a1c2e3g4i5k6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "employees",
        sa.Column("is_super_admin", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    op.drop_column("employees", "is_super_admin")
