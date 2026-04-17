"""add_submitted_by_to_timesheets

Revision ID: h7i8j9k0l1m2
Revises: g1h2i3j4k5l6
Create Date: 2026-04-08 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "h7i8j9k0l1m2"
down_revision: Union[str, None] = "g1h2i3j4k5l6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("timesheets", sa.Column("submitted_by", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_timesheets_submitted_by_employees",
        "timesheets",
        "employees",
        ["submitted_by"],
        ["id"],
    )
    # Preserve attribution for historical rows where possible.
    op.execute(
        """
        UPDATE timesheets
        SET submitted_by = employee_id
        WHERE submitted_at IS NOT NULL AND submitted_by IS NULL
        """
    )


def downgrade() -> None:
    op.drop_constraint("fk_timesheets_submitted_by_employees", "timesheets", type_="foreignkey")
    op.drop_column("timesheets", "submitted_by")
