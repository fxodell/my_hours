"""close_biweekly_periods_for_weekly_transition

Revision ID: a1b2c3d4e5f6
Revises: bf2d9b31f4c1
Create Date: 2026-03-16 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "bf2d9b31f4c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Close all existing open pay periods (bi-weekly) to prevent new entries.
    # Historical timesheets linked to these periods are preserved.
    # Admin can then generate new weekly Sun-Sat periods via the UI.
    op.execute(
        "UPDATE pay_periods SET status = 'closed' WHERE status = 'open'"
    )


def downgrade() -> None:
    # Cannot reliably reopen only the previously-open periods,
    # so this is a no-op. Admin can manually reopen periods if needed.
    pass
