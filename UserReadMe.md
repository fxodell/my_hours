# MyHours User Guide

MyHours is a mobile-first timesheet management app for tracking work hours, PTO, and submitting timesheets for approval.

---

## Getting Started

1. Open the app in your mobile browser or on desktop.
2. Log in with the email and password provided by your administrator.
3. If you forgot your password, tap **Forgot Password** on the login screen to receive a reset link.

After logging in you land on the **Dashboard**, which shows your current pay period, timesheet summary, and quick actions.

---

## For Employees

### Logging Time

1. Tap **Add Time** in the bottom nav (or the "Log Time" button on the Dashboard).
2. Fill in the form:
   - **Date** -- defaults to today; must be within the current pay period.
   - **Work Mode** -- Remote or On-Site.
   - **Client** -- select from the dropdown.
   - **Location** -- appears after selecting a client. Search/filter by typing.
   - **Job Code** -- appears after selecting a location (optional).
   - **Service Type** -- type of work performed.
   - **Hours** -- pick from the dropdown or use Start/End Time to auto-calculate.
   - **Vehicle Reimbursement** -- select a tier if applicable (on-site only).
   - **Description** -- optional notes about the work.
3. Tap **Save Entry**.

> **Can't find your site?** There is a "Request a new one" link right below the Location dropdown. See [Requesting a New Site](#requesting-a-new-site) below.

### Logging PTO

1. Tap **Add Time** on the Dashboard, then choose **Add PTO** (or navigate from a timesheet detail page).
2. Select the **Date**, **PTO Type** (Personal, Sick, Holiday, Other), and **Hours**.
3. Add optional notes and tap **Save**.

### Viewing & Managing Timesheets

Tap **Timesheets** in the bottom nav to see all your timesheets.

- **Draft** -- you can still add, edit, or delete entries.
- **Submitted** -- waiting for manager approval; read-only.
- **Approved** -- finalized; read-only.
- **Rejected** -- returned by your manager with a reason; you can edit and resubmit.

Tap any timesheet to see its detail page with all time and PTO entries, grouped by date.

### Editing & Deleting Entries

From a timesheet detail page (while the timesheet is in **draft** or **rejected** status):

- Tap an entry to edit it.
- Use the delete button to remove an entry (you'll be asked to confirm).

### Submitting a Timesheet

1. Open the timesheet detail page.
2. Review your entries and total hours.
3. Tap **Submit for Approval**.

Once submitted, the timesheet becomes read-only until your manager approves or rejects it.

### Resubmitting a Rejected Timesheet

If your timesheet is rejected, you'll see a banner with the rejection reason. Make the requested changes, then tap **Submit for Approval** again.

### Requesting a New Site

If you're working on a new well or AFE that isn't in the system:

1. Tap **Sites** in the bottom nav, then tap **Request New Site** (or use the link below the Location dropdown on the time entry form).
2. Fill in the form:
   - **Client** (required) -- the client this site belongs to.
   - **Site Name** (required) -- e.g. "Well Pad A-14".
   - **Region** -- e.g. "Alpine High" (optional).
   - **AFE / Job Code** -- the AFE number if known (optional).
   - **Job Code Description** -- brief description (optional).
   - **Notes** -- any additional context, e.g. "new well starting next week".
3. Tap **Submit Request**.

You can track the status of your requests on the **Sites** page:

- **Pending** (yellow) -- waiting for manager/admin review.
- **Approved** (green) -- the site has been created and is now available in the Location dropdown.
- **Rejected** (red) -- the request was declined; the reason is shown on the card.

### Changing Your Password

1. Tap **Profile** in the bottom nav.
2. Enter your current password, then your new password (minimum 6 characters) and confirm it.
3. Tap **Change Password**.

### Signing Out

Tap **Profile**, then scroll down and tap **Sign Out**.

---

## For Managers

Managers have access to everything employees do, plus approval and reporting tools.

### Approving & Rejecting Timesheets

1. Tap **Approve** in the bottom nav to see all submitted timesheets.
2. Tap a timesheet to expand it and review the entries (dates, hours, clients, descriptions).
3. Tap **Approve** to finalize it, or tap **Reject** to return it for corrections.
   - When rejecting, you must provide a reason. The employee will see this reason and can make changes before resubmitting.

### Managing Timesheets

Go to **Timesheets** to see all employee timesheets. You can filter by employee, status, or pay period.

- **Reopen as Draft** -- returns an approved or submitted timesheet to draft so the employee can make changes.
- **Delete** -- permanently removes a timesheet (use with caution).

### Reviewing & Approving Site Requests

1. Tap **Sites** in the bottom nav. As a manager, you see all requests from all employees.
2. Use the status filter to focus on **Pending** requests.
3. For each pending request:
   - **Approve** -- automatically creates the Location (and Job Code if an AFE was provided) in the system. The employee is notified and the site becomes available for time entry.
   - **Reject** -- opens a modal where you enter a reason. The employee is notified with your explanation.

Duplicate detection: if a location with the same client and site name already exists, approving will link to the existing location instead of creating a duplicate.

### Reports

Tap **Reports** from the Dashboard (or the manager tools section). Available reports:

- **Payroll Report** -- hours summary for a pay period (CSV export).
- **Billing Report** -- hours by client for billing (CSV export).
- **Engage Export** -- formatted export for the Engage payroll system.

Select a pay period and download the report.

---

## For Admins

Admins have full access to all manager features plus system configuration.

### Admin Tools (accessible from the Dashboard)

- **Employees** -- add, edit, activate/deactivate employee accounts. Set roles (manager, admin), pay period groups (A or B), and hourly rates.
- **Clients** -- manage the client list (name, industry).
- **Service Types** -- manage work categories (e.g. SCADA Services, Automation) and their billable status.
- **Locations** -- manage sites for each client, including region and active status. Add job codes to locations.
- **Pay Periods** -- view, generate, and close pay periods. Periods are grouped by A/B for staggered payroll schedules.

---

## Navigation Reference

The bottom navigation bar provides quick access to the main sections:

| Icon | Label | Who Can See | What It Does |
|------|-------|-------------|--------------|
| Home | Home | Everyone | Dashboard with summary and quick actions |
| Plus | Add Time | Everyone | Log a new time entry |
| Clipboard | Timesheets | Everyone | View and manage timesheets |
| Map Pin | Sites | Everyone | View and request new sites |
| Checkmark | Approve | Managers/Admins | Approve or reject submitted timesheets |
| Person | Profile | Everyone | Account settings, password change, sign out |

---

## Tips

- **Submit early.** Don't wait until Monday -- you can log time throughout the week.
- **Request sites ahead of time.** If you know you'll be working a new well next week, submit a site request as soon as you know. Managers can approve it before you need to enter time.
- **Check for rejections.** If your timesheet is rejected, you'll see it flagged on the Dashboard. Open it, read the reason, fix the entries, and resubmit.
- **Use the search** in the Location dropdown -- type part of the site name or region to filter a long list.
