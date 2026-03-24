# Claude Code CLI: Multi-tenant company isolation

Copy the block below into Claude Code CLI when implementing multi-company support in MyHours.

---

You are working in the MyHours repo. Implement multi-tenant company isolation with a safe, phased rollout.

IMPORTANT CONTEXT
- Stack: FastAPI + SQLAlchemy + Alembic backend, React + TS frontend.
- Current roles: employee, manager, admin using Employee.is_manager and Employee.is_admin.
- Current auth: JWT with user id in sub, role checks in backend/app/api/deps.py.
- Current system is single-tenant and must become multi-tenant.
- Goal: multiple companies can use the app, and users/data from one company are hidden from others.
- Also required: company CRUD and tenant-scoped password resets.
- Keep diffs scoped and incremental. Prefer migrations + tests first, then endpoint enforcement, then frontend updates.
- Do NOT introduce breaking architecture changes beyond this scope.

PHASED IMPLEMENTATION PLAN (DO IN ORDER)

PHASE 1 — Data model + migration foundation
1) Add new model:
   - backend/app/models/company.py
   Fields:
   - id (UUID via UUIDMixin)
   - name (string, required)
   - slug (string, unique, required)
   - is_active (bool default true)
   - timestamps via TimestampMixin
2) Register model exports in backend/app/models/__init__.py and schemas.
3) Add company_id FK (nullable initially) to:
   - employees
   - clients
   - service_types
   - pay_periods
   - timesheets
   - locations
   - job_codes
   - site_requests
   (and any other top-level business entities used in reports/queries)
4) Create Alembic migration(s):
   - create companies table
   - add company_id columns + FKs
   - backfill:
     - create default company row (e.g. name "Default Company", slug "default-company")
     - set company_id for all existing rows
   - set company_id NOT NULL after backfill
   - add tenant-scoped unique constraints where appropriate:
     - employees: keep global email unique OR migrate to (company_id, email) unique — choose and document decision
     - clients: (company_id, name) unique
     - pay_periods: (company_id, period_group, start_date) unique
     - any other prior global uniques that should be tenant-scoped
5) Update seed script so seeded admin and baseline data are tied to a company.

PHASE 2 — Schemas + auth context
1) Add company fields to schemas:
   - Employee response includes company_id (and optionally company_name).
   - Add CompanyCreate/Update/Response schemas.
2) Update auth:
   - include company_id in /auth/me response.
   - optionally include company_id in JWT claims (do not break existing token handling).
3) Add helper/dependency utilities for tenant scope in backend/app/api/deps.py:
   - e.g. helper that returns current_user.company_id
   - use this consistently in endpoints.

PHASE 3 — Company CRUD endpoints
1) Add backend/app/api/companies.py with endpoints:
   - GET /api/companies
   - GET /api/companies/{id}
   - POST /api/companies
   - PATCH /api/companies/{id}
   - DELETE /api/companies/{id} (soft delete via is_active=false)
2) Decide/implement permissions:
   - introduce platform-level super admin capability (recommended) OR keep restricted to existing admin if explicitly documented.
   - If introducing super-admin, add Employee.is_super_admin bool + checks in deps.
3) Register router in backend/app/main.py.

PHASE 4 — Enforce tenant isolation in backend endpoints
For every endpoint below, enforce company filtering and company-consistent joins:
- employees.py
- timesheets.py
- reports.py
- clients.py
- locations.py
- service_types.py
- pay_periods.py
- site_requests.py
Rules:
- Non-manager users: only own records AND own company.
- Manager/admin: only records in current_user.company_id.
- Admin create/update/delete actions must not cross company boundary unless super-admin.
- For ID-based fetch/update/delete, return 404 (or 403 with consistent policy) when record is outside company.
- Ensure related entities belong to same company before creating references (e.g. time entry client/location/job code must match timesheet company).

PHASE 5 — Tenant-scoped password reset behavior
1) Keep self-service reset flow working.
2) Update admin reset password endpoint:
   - admin can reset only employees in same company.
   - super-admin (if implemented) can reset any company.
3) Add audit-style logging hook for admin reset events (basic structured log is fine).

PHASE 6 — Frontend updates
1) Update types:
   - frontend/src/types/index.ts User includes company_id (and optional company_name).
   - add Company type.
2) Add API methods in frontend/src/services/api.ts for company CRUD.
3) Add admin UI page for companies (create/update/deactivate) and route guard.
4) Ensure employee/admin pages pass and display company context as needed.
5) Do not rely on frontend-only filtering for security; backend must enforce.

PHASE 7 — Tests (required)
Add/extend backend tests to prove isolation:
1) Two-company fixture setup.
2) Employees:
   - manager/admin from company A cannot list/get/update/delete company B employees.
3) Timesheets:
   - cross-company access denied for list/get/approve/reject/reopen/delete.
4) Reports:
   - manager from company A only receives company A data.
5) Password reset:
   - company admin cannot reset company B user.
6) Company CRUD:
   - permissions and soft-delete behavior.
7) Existing tests should still pass.

PHASE 8 — Docs update
1) Update docs/CONTEXT.md:
   - new multi-tenant model
   - role semantics (company-scoped)
   - company CRUD and reset-password rules
2) Keep CLAUDE.md guidance intact; only adjust if behavior changed.

IMPLEMENTATION RULES
- Make small, reviewable commits in logical chunks.
- Avoid unrelated refactors.
- Preserve current endpoint contracts as much as possible; document any unavoidable API changes.
- Run backend tests and report results.
- If frontend changed, run lint/build and report results.
- At the end, provide:
  1) list of files changed
  2) migration summary
  3) permission model summary before/after
  4) test summary
  5) any follow-up risks.

Start with PHASE 1 and PHASE 2 only. Stop and summarize before moving to PHASE 3.
