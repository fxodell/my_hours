"""merge_heads_after_billing_weeks

Revision ID: f1a2b3c4d5e6
Revises: d4e5f6a7b8c9, e9f1c2d3a4b5
Create Date: 2026-03-23 00:00:01.000000

"""
from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, tuple[str, str], None] = ("d4e5f6a7b8c9", "e9f1c2d3a4b5")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
