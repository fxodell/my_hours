"""add companies table and company_id to all entities

Revision ID: a1c2e3g4i5k6
Revises: f1a2b3c4d5e6
Create Date: 2026-03-24 00:00:00.000000

Design decisions:
- Email remains globally unique (not tenant-scoped) so login by email alone works.
- Client name becomes (company_id, name) unique instead of globally unique.
- Service type name becomes (company_id, name) unique instead of globally unique.
- Pay period unique constraint becomes (company_id, period_group, start_date).
- A default company is created and all existing rows are backfilled to it.
"""
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = "a1c2e3g4i5k6"
down_revision: Union[str, None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Fixed UUID for the default company so it can be referenced in backfill
DEFAULT_COMPANY_ID = uuid.UUID("00000000-0000-4000-a000-000000000001")


def upgrade() -> None:
    # 1. Create companies table
    op.create_table(
        "companies",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(200), nullable=False, unique=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 2. Insert default company
    op.execute(
        sa.text(
            "INSERT INTO companies (id, name, slug, is_active) "
            "VALUES (:id, :name, :slug, true)"
        ).bindparams(
            id=DEFAULT_COMPANY_ID,
            name="Default Company",
            slug="default-company",
        )
    )

    # 3. Add nullable company_id columns to all entities
    tables = [
        "employees", "clients", "service_types", "pay_periods",
        "timesheets", "locations", "job_codes", "site_requests",
    ]
    for table in tables:
        op.add_column(table, sa.Column("company_id", UUID(as_uuid=True), nullable=True))

    # 4. Backfill all existing rows with the default company
    for table in tables:
        op.execute(
            sa.text(f"UPDATE {table} SET company_id = :cid").bindparams(cid=DEFAULT_COMPANY_ID)
        )

    # 5. Set NOT NULL after backfill
    for table in tables:
        op.alter_column(table, "company_id", nullable=False)

    # 6. Add foreign key constraints
    for table in tables:
        op.create_foreign_key(
            f"fk_{table}_company_id",
            table,
            "companies",
            ["company_id"],
            ["id"],
            ondelete="CASCADE",
        )

    # 7. Add indexes on company_id
    for table in tables:
        op.create_index(f"ix_{table}_company_id", table, ["company_id"])

    # 8. Replace old unique constraints with tenant-scoped ones

    # clients: drop global unique on name, add (company_id, name)
    op.drop_constraint("clients_name_key", "clients", type_="unique")
    op.create_unique_constraint("uq_client_company_name", "clients", ["company_id", "name"])

    # service_types: drop global unique on name, add (company_id, name)
    op.drop_constraint("service_types_name_key", "service_types", type_="unique")
    op.create_unique_constraint("uq_service_type_company_name", "service_types", ["company_id", "name"])

    # pay_periods: drop old (period_group, start_date), add (company_id, period_group, start_date)
    op.drop_constraint("uq_pay_period_group_start", "pay_periods", type_="unique")
    op.create_unique_constraint(
        "uq_pay_period_company_group_start",
        "pay_periods",
        ["company_id", "period_group", "start_date"],
    )


def downgrade() -> None:
    # Reverse tenant-scoped unique constraints
    op.drop_constraint("uq_pay_period_company_group_start", "pay_periods", type_="unique")
    op.create_unique_constraint("uq_pay_period_group_start", "pay_periods", ["period_group", "start_date"])

    op.drop_constraint("uq_service_type_company_name", "service_types", type_="unique")
    op.create_unique_constraint("service_types_name_key", "service_types", ["name"])

    op.drop_constraint("uq_client_company_name", "clients", type_="unique")
    op.create_unique_constraint("clients_name_key", "clients", ["name"])

    # Remove company_id columns and FKs
    tables = [
        "employees", "clients", "service_types", "pay_periods",
        "timesheets", "locations", "job_codes", "site_requests",
    ]
    for table in tables:
        op.drop_index(f"ix_{table}_company_id", table)
        op.drop_constraint(f"fk_{table}_company_id", table, type_="foreignkey")
        op.drop_column(table, "company_id")

    # Drop companies table
    op.drop_table("companies")
