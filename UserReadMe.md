# MyHours User Guide

MyHours is a mobile-first timesheet management app for tracking work hours, PTO, and submitting timesheets for approval.

---

## Getting Started

1. Open the app in your mobile browser or on desktop.
2. Log in with the email and password provided by your administrator.
3. If you forgot your password, tap **Forgot Password** on the login screen to receive a reset link via email.

After logging in you land on the **Dashboard**.

---

## The Dashboard

The Dashboard is your home screen. It shows:

- **Greeting** with your name and current pay period dates.
- **Current Timesheet Card** -- your timesheet status (Draft, Submitted, Approved, Rejected) and total hours logged, with buttons to **Add Time** or **View Details**.
- **Past Timesheets Needing Attention** -- any draft or rejected timesheets from recent pay periods that still need action.
- **Rejected Timesheet Alert** -- a red banner appears if your current timesheet was rejected, showing the manager's reason and linking to the timesheet.
- **Quick Actions** -- shortcuts to Log Time, View Timesheets, Add PTO, and Location Requests.
- **Admin Tools** (managers and admins only) -- links to Reports, Employees, Clients, Service Types, Locations, and Pay Periods.

---

## For Employees

### Logging Time

1. Tap **Add Time** in the bottom nav (or the "Log Time" button on the Dashboard).
2. Fill in the form:
   - **Date** -- defaults to today; must be within the selected pay period.
   - **Duration** -- choose one (they are mutually exclusive):
     - **Start & end time** -- enter start and end clock times; hours worked are computed automatically (rounded to the nearest quarter hour), or
     - **Hours worked** -- tap a button to set hours (0.5, 1, 1.5, ... up to 12) without using clock times.
   - **Work Mode** -- tap **Remote** or **On-Site**.
   - **Client** -- select from the dropdown.
   - **Location** -- appears after selecting a client. Type to search and filter the list.
   - **Job Code** -- appears after selecting a location (optional).
   - **Service Type** -- type of work performed.
   - **Description of Work** -- optional notes about the work.
   - **Personal Vehicle Reimbursement** (on-site only) -- select a tier:
     - None
     - Less than 3 Hours -- $30
     - 3 to 5 Hours -- $60
     - 5.5 to 6 Hours -- $90
     - More than 6 Hours -- $120
   - **Pay Period** -- if you have more than one open pay period, you can choose which one to log time against.
3. Tap **Save Entry**.

> **Can't find your location?** Use **Request a new one** under the Location dropdown to submit a location request from the time entry form without leaving the page. See [Requesting a new location](#requesting-a-new-location) below.

> **Billing week locked?** If a billing week has been approved or marked as billed by a manager, you cannot add or edit entries for dates in that week.

### Logging PTO

1. Tap **Add PTO** from the Dashboard quick actions, or from a timesheet detail page.
2. Fill in the form:
   - **Date** -- must be within the pay period.
   - **PTO Type** -- tap one of four buttons: Personal Time Off, Sick Leave, Holiday, or Other.
   - **Hours** -- tap a button to select hours (1 through 8).
   - **Notes** -- optional.
3. Tap **Save PTO Entry**.

### Viewing & Managing Timesheets

Tap **Timesheets** in the bottom nav to see all your timesheets. Each card shows the pay period dates, total hours, last updated time, and status:

- **Draft** -- you can still add, edit, or delete entries.
- **Submitted** -- waiting for manager approval; read-only.
- **Approved** -- finalized; read-only.
- **Rejected** -- returned by your manager with a reason displayed on the card; you can edit and resubmit.

Tap any timesheet to open its detail page.

### Timesheet Detail Page

The detail page shows:

- **Status badge** and pay period dates.
- **Rejection reason** (if rejected) in a banner at the top.
- **Billing Week Status** -- cards showing the status of each week (Open, Submitted, Approved, Billed).
- **Summary card** -- total hours with a breakdown of work hours vs. PTO hours.
- **Time entries** grouped by date, showing hours, client, service type, work mode, description, and start/end times if provided.
- **PTO entries** showing hours, PTO type, date, and notes.
- **Add Time** and **Add PTO** buttons (when the timesheet is editable).

### Editing & Deleting Entries

From the timesheet detail page (while the timesheet is in **Draft** or **Rejected** status):

- Tap the edit icon on an entry to edit it.
- Tap the delete icon to remove an entry (you'll be asked to confirm).

Entries in weeks that have been approved or billed cannot be edited.

### Submitting a Timesheet

1. Open the timesheet detail page.
2. Review your entries and total hours.
3. Tap **Submit for Approval**.

You must have at least one entry to submit. Once submitted, the timesheet becomes read-only until your manager approves or rejects it.

### Resubmitting a Rejected Timesheet

If your timesheet is rejected, you'll see a red alert banner on the Dashboard with the rejection reason. The timesheet also appears in the "Past Timesheets Needing Attention" section. Open it, make the requested changes, then tap **Submit for Approval** again.

### Requesting a new location

If you're working at a new well or AFE that isn't in the system:

1. Tap **Loc. reqs** in the bottom nav, then tap **Request New Location** (or use the inline request form on the time entry page).
2. Fill in the form:
   - **Client** (required) -- the client this location belongs to.
   - **Location name** (required) -- e.g. "Well Pad A-14".
   - **Region** -- e.g. "Alpine High" (optional).
   - **AFE / Job Code** -- the AFE number if known (optional).
   - **Job Code Description** -- brief description (optional).
   - **Notes** -- any additional context, e.g. "new well starting next week".
3. Tap **Submit Request**.

You can track the status of your requests on the **Location Requests** page (**Loc. reqs** in the bottom nav):

- **Pending** (yellow) -- waiting for manager/admin review.
- **Approved** (green) -- the location has been created and is now available in the Location dropdown.
- **Rejected** (red) -- the request was declined; the reason is shown on the card.

### My Time Detail Report

All employees can export their own time entries:

1. Tap **Reports** in the bottom nav.
2. Under **My Time Detail**, select a date range.
3. Optionally filter by timesheet status, pay period status, and whether to include PTO.
4. Tap **Preview** to see a summary table, or **Download** as CSV or Excel.

### Profile

Tap **Profile** in the bottom nav to see:

- Your name, email, and initials avatar.
- **Hire Date**, **Pay Period Group** (A or B), and **Role** (Employee, Manager, Admin, or Super Admin).
- **Administration links** (admins only) -- quick access to Employees, Clients, Service Types, Locations, Pay Periods, and Companies.

### Changing Your Password

1. Tap **Profile** in the bottom nav.
2. Tap **Change** next to the password section.
3. Enter your current password, then your new password (minimum 6 characters) and confirm it.
4. Tap **Change Password**.

### Signing Out

Tap **Profile**, then scroll down and tap **Sign Out**.

---

## For Managers

Managers have access to everything employees do, plus approval, reporting, and billing week management tools.

### Approving & Rejecting Timesheets

1. Tap **Approve** in the bottom nav to see all submitted timesheets.
2. Tap a timesheet to expand it and review the entries (dates, hours, clients, descriptions).
3. Tap **Approve** to finalize it, or tap **Reject** to return it for corrections.
   - When rejecting, you must provide a reason. The employee will see this reason and can make changes before resubmitting.

The employee receives a notification when their timesheet is approved or rejected.

### Managing Timesheets

Go to **Timesheets** to see all employee timesheets. You can filter by:

- **Employee** -- select a specific employee from the dropdown.
- **Status** -- Draft, Submitted, Approved, or Rejected.
- **Pay Period** -- select a specific pay period.

Manager actions on each timesheet:

- **Reopen as Draft** -- returns an approved or submitted timesheet to draft so the employee can make changes.
- **Delete** -- permanently removes a timesheet (requires confirmation).

### Managing Billing Weeks

On a timesheet detail page, managers can manage billing week status per week:

- **Submit** -- mark an open/reopened week as submitted.
- **Approve** -- approve a submitted week (locks entries in that week from editing).
- **Mark Billed** -- mark an approved week as billed.
- **Reopen** -- reopen a submitted, approved, or billed week.

### Reviewing & approving location requests

1. Tap **Loc. reqs** in the bottom nav. As a manager, you see all requests from all employees.
2. Use the status filter to focus on **Pending** requests.
3. For each pending request:
   - **Approve** -- automatically creates the Location (and Job Code if an AFE was provided) in the system. The employee is notified and the location appears in the Location dropdown for time entry (refresh or revisit the page if you already had the form open).
   - **Reject** -- opens a modal where you enter a reason. The employee is notified with your explanation.

Duplicate detection: if a location with the same client and site name already exists, approving will link to the existing location instead of creating a duplicate.

### Reports

Tap **Reports** in the bottom nav or from the Dashboard admin tools section. Manager reports include:

#### Employee Detail Report
Export detailed time entries for one or more employees.
- Select a date range.
- Filter by timesheet status, pay period status, and whether to include PTO.
- Select employees individually or use **Select All**.
- Preview shows row counts, work hours, PTO hours, and a per-employee summary table.
- Download as CSV or Excel.

#### Biweekly Payroll Rollup
One row per employee for two consecutive weeks with per-day hour breakdowns.
- Select **Pay Group** (A or B) and a starting pay period.
- Preview shows employee count, date range, and data quality warnings.
- Table columns: employee name, daily hours for each day, then Regular, OT, PTO, and Total.
- Download as CSV or Excel.

#### Pay Period Reports
Select a pay period, then access three sub-reports:

- **Payroll Report** -- employee hours summary with Regular, OT, PTO, and Total columns. Preview available. Download as CSV.
- **Billing Report** -- hours grouped by client for invoicing. Preview shows client-level summary with expandable line-item detail (date, client, location, employee, service, hours). Download as CSV.
- **Engage Export** -- formatted export for the Engage payroll system. Download as CSV (no preview).

---

## For Admins

Admins have full access to all manager features plus system configuration.

### Admin Tools (accessible from the Dashboard or Profile page)

- **Employees** -- add, edit, activate/deactivate employee accounts. Set roles (manager, admin), pay period groups (A or B), and hourly rates.
- **Clients** -- manage the client list (name, industry).
- **Service Types** -- manage work categories (e.g. SCADA Services, Automation) and their billable status.
- **Locations** -- manage sites for each client, including region and active status. Add job codes to locations.
- **Pay Periods** -- view, generate, and close pay periods. Periods are grouped by A/B for staggered payroll schedules.
- **Reset Passwords** -- admins can reset any employee's password within their company.

---

## Timesheet Workflow

The lifecycle of a timesheet follows this flow:

```
Draft  -->  Submitted  -->  Approved
                |
                v
            Rejected  -->  (edit & resubmit)  -->  Submitted
```

- **Draft**: Employee adds, edits, and deletes time and PTO entries.
- **Submitted**: Employee taps "Submit for Approval." Timesheet becomes read-only. Manager is notified.
- **Approved**: Manager approves. Timesheet is finalized and read-only. Employee is notified.
- **Rejected**: Manager rejects with a reason. Timesheet returns to an editable state. Employee is notified and can make changes and resubmit.
- **Reopened to Draft**: A manager can reopen a submitted or approved timesheet back to draft at any time, allowing the employee to make further changes.

### Billing Weeks (within a timesheet)

Each timesheet is divided into weekly billing periods. Managers can manage these independently:

```
Open  -->  Submitted  -->  Approved  -->  Billed
                                |
                           Reopen (back to open)
```

When a billing week is approved or billed, entries for dates in that week are locked and cannot be edited or deleted by the employee.

---

## Navigation Reference

The bottom navigation bar is organized in two rows:

**Row 1 -- Primary Actions (always visible):**

| Icon | Label | Who Can See | What It Does |
|------|-------|-------------|--------------|
| Home | Home | Everyone | Dashboard with summary and quick actions |
| Plus | Add Time | Everyone | Log a new time entry |
| Clipboard | Timesheets | Everyone | View and manage timesheets |

**Row 2 -- Secondary Actions:**

| Icon | Label | Who Can See | What It Does |
|------|-------|-------------|--------------|
| Map Pin | Loc. reqs | Everyone | View and request new locations |
| Checkmark | Approve | Managers/Admins | Approve or reject submitted timesheets |
| Chart | Reports | Everyone | View and download reports |
| Person | Profile | Everyone | Account info, password change, sign out |

---

## Pay Period Groups

Employees are assigned to Pay Period Group **A** or **B**. These are alternating two-week cycles that stagger payroll processing. You will only see pay periods and timesheets for your assigned group. Your group is shown on your Profile page.

---

## Tips

- **Submit early.** Don't wait until the end of the pay period -- log time throughout the week so nothing is forgotten.
- **Request locations ahead of time.** If you know you'll be working a new well next week, submit a location request as soon as you know. Managers can approve it before you need to enter time.
- **Check for rejections.** If your timesheet is rejected, you'll see a red alert on the Dashboard. Open it, read the reason, fix the entries, and resubmit.
- **Use the search** in the Location dropdown -- type part of the site name or region to filter a long list.
- **Use Start & end time** under Duration when you want clock-based hours; otherwise choose **Hours worked** and tap the hour you need -- pick one mode per entry, not both.
- **Check your Profile** to confirm your pay period group and role.
- **Export your own time** using the "My Time Detail" report under Reports -- you don't need to be a manager to download your own entries.
