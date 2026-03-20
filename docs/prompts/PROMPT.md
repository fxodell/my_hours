# Prompt Templates

## Common Prompts
<!-- Store useful prompts for AI assistants here -->

## Project-Specific Instructions
<!-- Custom instructions for this codebase -->

### Site Request Workflow
The site request workflow (employee submits → manager approves → Location/JobCode created) is fully documented in `docs/CONTEXT.md` under "Site request workflow" and in `docs/DECISIONS.md` (ADR-001). Key files: `backend/app/api/site_requests.py`, `backend/app/models/site_request.py`, `frontend/src/pages/SiteRequests.tsx`, `frontend/src/pages/SiteRequestForm.tsx`, and the inline request form in `frontend/src/pages/TimeEntry.tsx`.

### Billing Report — Location and Site Code
To add location (site) and site code (job code) columns to the Billing report, use the prompt in `docs/prompts/PROMPT_BILLING_LOCATION_SITE_CODE.md`. It specifies backend changes in `backend/app/api/reports.py` and doc updates in CONTEXT.md, TASKS.md, and optionally DECISIONS.md.
