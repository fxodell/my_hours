"""split_biweekly_to_weekly_periods

Revision ID: g1h2i3j4k5l6
Revises: cb13541195a4
Create Date: 2026-04-06 00:00:00.000000

"""
from typing import Sequence, Union
from datetime import date, timedelta
import uuid

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "g1h2i3j4k5l6"
down_revision: Union[str, None] = "cb13541195a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Close stale open biweekly periods (Mar 15-28) — past grace window
    conn.execute(
        sa.text(
            "UPDATE pay_periods SET status = 'closed' "
            "WHERE status = 'open' AND start_date = '2026-03-15' AND end_date = '2026-03-28'"
        )
    )

    # 2. Split active biweekly periods (Mar 29 - Apr 11) into Week 1 (Mon-Sun)
    #    Truncate to Mar 30 - Apr 5. All entries are Mar 30-Apr 4, no entries on Mar 29.
    conn.execute(
        sa.text(
            "UPDATE pay_periods SET start_date = '2026-03-30', end_date = '2026-04-05' "
            "WHERE status = 'open' AND start_date = '2026-03-29' AND end_date = '2026-04-11'"
        )
    )

    # 3. Delete misaligned billing week 1 (Mar 23-29) from timesheets in the split period.
    #    These billing weeks were created by the old _get_two_monday_sunday_weeks function
    #    and fall outside the new period bounds. No entries exist in this range.
    conn.execute(
        sa.text(
            "DELETE FROM billing_weeks "
            "WHERE week_start_date = '2026-03-23' AND week_end_date = '2026-03-29' "
            "AND timesheet_id IN ("
            "  SELECT t.id FROM timesheets t "
            "  JOIN pay_periods pp ON pp.id = t.pay_period_id "
            "  WHERE pp.start_date = '2026-03-30' AND pp.end_date = '2026-04-05'"
            ")"
        )
    )

    # 4. Create Week 2 period (Apr 6-12) for each company/group that had the split period
    result = conn.execute(
        sa.text(
            "SELECT DISTINCT company_id, period_group FROM pay_periods "
            "WHERE start_date = '2026-03-30' AND end_date = '2026-04-05'"
        )
    )
    companies_groups = [(row[0], row[1]) for row in result]

    for company_id, period_group in companies_groups:
        # Create Week 2: Apr 6 (Mon) - Apr 12 (Sun)
        conn.execute(
            sa.text(
                "INSERT INTO pay_periods (id, company_id, period_group, start_date, end_date, status, created_at, updated_at) "
                "VALUES (:id, :company_id, :period_group, '2026-04-06', '2026-04-12', 'open', NOW(), NOW())"
            ),
            {"id": str(uuid.uuid4()), "company_id": str(company_id), "period_group": period_group},
        )

        # Generate 8 future weekly Mon-Sun periods starting Apr 13
        for i in range(8):
            period_start = date(2026, 4, 13) + timedelta(days=7 * i)
            period_end = period_start + timedelta(days=6)
            conn.execute(
                sa.text(
                    "INSERT INTO pay_periods (id, company_id, period_group, start_date, end_date, status, created_at, updated_at) "
                    "VALUES (:id, :company_id, :period_group, :start_date, :end_date, 'open', NOW(), NOW())"
                ),
                {
                    "id": str(uuid.uuid4()),
                    "company_id": str(company_id),
                    "period_group": period_group,
                    "start_date": period_start.isoformat(),
                    "end_date": period_end.isoformat(),
                },
            )


def downgrade() -> None:
    # Revert the split: restore original biweekly period dates
    conn = op.get_bind()

    # Delete generated future weekly periods (Apr 6 onward)
    conn.execute(
        sa.text(
            "DELETE FROM pay_periods WHERE start_date >= '2026-04-06' "
            "AND (end_date - start_date) = 6"
        )
    )

    # Restore original biweekly dates on the split period
    conn.execute(
        sa.text(
            "UPDATE pay_periods SET start_date = '2026-03-29', end_date = '2026-04-11' "
            "WHERE start_date = '2026-03-30' AND end_date = '2026-04-05'"
        )
    )

    # Reopen stale periods
    conn.execute(
        sa.text(
            "UPDATE pay_periods SET status = 'open' "
            "WHERE start_date = '2026-03-15' AND end_date = '2026-03-28' AND status = 'closed'"
        )
    )
