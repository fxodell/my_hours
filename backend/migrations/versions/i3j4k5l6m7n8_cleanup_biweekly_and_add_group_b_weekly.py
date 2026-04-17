"""cleanup_biweekly_and_add_group_b_weekly

Revision ID: i3j4k5l6m7n8
Revises: h7i8j9k0l1m2
Create Date: 2026-04-16 00:00:00.000000

- Delete the one empty biweekly draft timesheet left behind after the Mon-Sun split
  (phillip@bnbenergy.com, 2026-03-15 to 2026-03-28). Other residual biweekly drafts
  that still contain real entries are left alone so the employees can submit them.
- Generate Mon-Sun weekly pay periods for Group B (both companies) from 2026-04-20
  through 2026-06-07, bringing Group B onto the same weekly cadence as Group A.

"""
from typing import Sequence, Union
from datetime import date, timedelta
import uuid

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "i3j4k5l6m7n8"
down_revision: Union[str, None] = "h7i8j9k0l1m2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Delete the empty biweekly draft timesheet for phillip@bnbenergy.com
    conn.execute(
        sa.text(
            """
            DELETE FROM timesheets
            WHERE status = 'draft'
              AND employee_id = (SELECT id FROM employees WHERE email = 'phillip@bnbenergy.com')
              AND pay_period_id IN (
                SELECT id FROM pay_periods
                WHERE start_date = '2026-03-15' AND end_date = '2026-03-28'
              )
              AND NOT EXISTS (SELECT 1 FROM time_entries WHERE timesheet_id = timesheets.id)
              AND NOT EXISTS (SELECT 1 FROM pto_entries WHERE timesheet_id = timesheets.id)
            """
        )
    )

    # 2. Generate Group B Mon-Sun weekly pay periods (Apr 20 - Jun 7) for each company
    result = conn.execute(
        sa.text("SELECT DISTINCT company_id FROM pay_periods WHERE period_group = 'B'")
    )
    company_ids = [row[0] for row in result]

    for company_id in company_ids:
        for i in range(8):
            period_start = date(2026, 4, 20) + timedelta(days=7 * i)
            period_end = period_start + timedelta(days=6)

            existing = conn.execute(
                sa.text(
                    "SELECT id FROM pay_periods "
                    "WHERE company_id = :cid AND period_group = 'B' AND start_date = :start"
                ),
                {"cid": str(company_id), "start": period_start.isoformat()},
            ).scalar()

            if not existing:
                conn.execute(
                    sa.text(
                        "INSERT INTO pay_periods (id, company_id, period_group, start_date, end_date, status, created_at, updated_at) "
                        "VALUES (:id, :cid, 'B', :start, :end, 'open', NOW(), NOW())"
                    ),
                    {
                        "id": str(uuid.uuid4()),
                        "cid": str(company_id),
                        "start": period_start.isoformat(),
                        "end": period_end.isoformat(),
                    },
                )


def downgrade() -> None:
    conn = op.get_bind()

    # Remove the Group B weekly pay periods this migration created
    conn.execute(
        sa.text(
            "DELETE FROM pay_periods "
            "WHERE period_group = 'B' "
            "AND start_date >= '2026-04-20' AND start_date <= '2026-06-01' "
            "AND (end_date - start_date) = 6"
        )
    )

    # Phillip's empty draft deletion is intentionally not recreated in downgrade
