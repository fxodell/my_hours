# Prompt: Read and Update All docs/*.md — Site Request Workflow

**Instructions for Claude:** Read every markdown file in the `docs/` folder and update them so they fully document the following. After making changes, ensure the docs answer these questions clearly.

## Questions to Answer in the Docs

1. **When a user submits a new location to be added, where does it go?**
   - Submissions are **site requests** (not locations yet). They are stored in the `site_requests` table in the database.
   - Any authenticated user (including normal employees) can create a site request via:
     - **Time entry flow:** On the Add Time page, after selecting a client, if their location isn’t in the list they can click “Request a new site” and submit an inline form (client, site name, region, optional job code/description, notes).
     - **Standalone form:** Navigate to **Site Requests** (e.g. from Dashboard or `/site-requests`) and use “New request” or `/site-requests/new`.
   - API: `POST /api/site-requests` creates a site request with status `pending`. Managers are notified by email (in production; in dev, email is logged).

2. **How can someone approve and add it?**
   - **Who:** Only **managers** (or admins) can approve or reject site requests. Employees can only create requests and view their own.
   - **Where:** Managers open the **Site Requests** page at `/site-requests` (linked from the Dashboard for managers). They see all requests (optionally filtered by status: pending, approved, rejected).
   - **Approve:** Click **Approve** on a pending request. The backend:
     - Creates a new **Location** for that client with the requested site name and region (and optionally a **JobCode** if job code info was provided).
     - Sets the site request status to `approved`, sets `reviewed_by` and `reviewed_at`, and stores `created_location_id` (and `created_job_code_id` if a job code was created).
     - Sends an email to the requesting employee (in production).
   - **Reject:** Click **Reject**, provide a reason. Status is set to `rejected` and the employee is notified. No location or job code is created.
   - API: `POST /api/site-requests/{id}/approve` (manager only), `POST /api/site-requests/{id}/reject` (manager only, body: `rejection_reason`).

## Docs to Read and Update

- **CONTEXT.md** — Add a short “Site requests” subsection under the domain workflow or a dedicated section: what they are, where submissions go (DB + who can see them), and that managers approve/reject from the Site Requests page (and that approving creates the Location/JobCode). Mention the Time Entry “Request a new site” flow and the standalone `/site-requests` and `/site-requests/new` routes.
- **TASKS.md** — If site request work is done, ensure it’s under Completed; if there are open follow-ups (e.g. email in production), add them to Current Sprint or Backlog as appropriate.
- **DECISIONS.md** — Optionally add an ADR for “Site request workflow (employee request → manager approve → Location/JobCode creation)” if not already covered.
- **PROMPT.md** — Optionally add a reference to this prompt or a one-line note that site request workflow is documented in CONTEXT and in this file.
- **PROMPT_USER.md** — Only if it’s the right place for user-facing instructions; otherwise leave it as is or add a single sentence pointing to “Site Requests” and where to approve (manager view).

## Requirements

- Use the exact behavior of the codebase (see `backend/app/api/site_requests.py`, `frontend/src/pages/SiteRequests.tsx`, `frontend/src/pages/TimeEntry.tsx` “Request a new site”, and `frontend/src/App.tsx` routes).
- Keep existing structure and tone of each doc; only add or adjust sections needed to answer “where does it go?” and “how do I approve and add it?”
- Do not change backend or frontend code; only update `docs/*.md`.
