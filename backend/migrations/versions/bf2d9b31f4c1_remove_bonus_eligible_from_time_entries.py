"""remove_bonus_eligible_from_time_entries

Revision ID: bf2d9b31f4c1
Revises: 801b03186c43
Create Date: 2026-02-23 22:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "bf2d9b31f4c1"
down_revision: Union[str, None] = "801b03186c43"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("time_entries", "bonus_eligible")


def downgrade() -> None:
    op.add_column(
        "time_entries",
        sa.Column("bonus_eligible", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.alter_column("time_entries", "bonus_eligible", server_default=None)
