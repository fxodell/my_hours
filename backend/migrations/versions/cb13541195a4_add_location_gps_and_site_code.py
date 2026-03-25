"""add_location_gps_and_site_code

Revision ID: cb13541195a4
Revises: b2d3f4h5j6l7
Create Date: 2026-03-25 22:30:18.455812

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cb13541195a4'
down_revision: Union[str, None] = 'b2d3f4h5j6l7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "locations",
        sa.Column("latitude", sa.Numeric(precision=11, scale=8), nullable=True),
    )
    op.add_column(
        "locations",
        sa.Column("longitude", sa.Numeric(precision=11, scale=8), nullable=True),
    )
    op.add_column(
        "locations",
        sa.Column("site_code", sa.String(length=80), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("locations", "site_code")
    op.drop_column("locations", "longitude")
    op.drop_column("locations", "latitude")
