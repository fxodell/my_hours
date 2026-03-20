# Prompt: Grace Period for Retroactive Time & PTO Entry on Closed Pay Periods

## Problem Statement

Users cannot add time or PTO entries for dates like January 24, 2026 when today is February 25, 2026. The previous fix (multi-period selector with 45-day window) only surfaces **open** pay periods. Once an admin closes a pay period, it becomes completely invisible and inaccessible — no grace period exists for late entries.

This is a common real-world scenario: an employee forgets to log time, the pay period ends, an admin closes it, and now the employee has no way to go back and enter their hours.

## Root Cause: 6 Hard Walls Against Closed Periods

Every layer of the stack rejects closed pay periods:

| # | Constraint | Location | Effect |
|---|---|---|---|
| 1 | `GET /pay-periods/recent` filters `status == "open"` | `pay_periods.py:88` | Closed periods never returned to frontend |
| 2 | `GET /pay-periods/current` filters `status == "open"` | `pay_periods.py:48` | Current timesheet lookup skips closed periods |
| 3 | `GET /timesheets/for-period/{id}` rejects `status != "open"` | `timesheets.py:148-152` | Cannot get/create timesheet for closed period |
| 4 | `create_time_entry` checks timesheet status, not period status | `timesheets.py:483` | Blocks if timesheet is submitted/approved |
| 5 | `create_pto_entry` checks timesheet status, not period status | `timesheets.py:692` | Same as above for PTO |
| 6 | Pay period model has statuses: `open`, `closed`, `processed` | `pay_period.py:24` | No intermediate "grace" state |

**Key insight:** Constraints #4 and #5 only check **timesheet** status (`draft`/`rejected` = editable). They do NOT check pay period status. So if we can get a user to a draft timesheet for a closed period, the create/update entry endpoints will already accept it. The blockers are #1, #2, and #3 — the lookup/access layer, not the mutation layer.

## Proposed Solution: Grace Period on Closed Pay Periods

Add a **grace period** (default: 7 days after `end_date`) during which closed pay periods remain accessible for entry. The period is closed for payroll purposes but still allows employees to add or edit entries on draft/rejected timesheets.

### Step 1: Update `GET /pay-periods/recent` — Include Recently-Closed Periods

**File:** `backend/app/api/pay_periods.py`

Currently filters `status == "open"`. Change to also include `closed` periods whose `end_date` is within the grace window.

```python
GRACE_PERIOD_DAYS = 7

@router.get("/recent")
async def get_recent_pay_periods(...):
    today = date.today()
    cutoff = today - timedelta(days=45)
    grace_cutoff = today - timedelta(days=GRACE_PERIOD_DAYS)

    result = await db.execute(
        select(PayPeriod)
        .where(PayPeriod.period_group == current_user.pay_period_group)
        .where(PayPeriod.start_date <= today)
        .where(PayPeriod.end_date >= cutoff)
        .where(
            or_(
                PayPeriod.status == "open",
                and_(
                    PayPeriod.status == "closed",
                    PayPeriod.end_date >= grace_cutoff,
                ),
            )
        )
        .order_by(PayPeriod.start_date.desc())
    )
    return list(result.scalars().all())
```

This means: return all open periods in the 45-day window, PLUS any closed periods whose end_date is within the last 7 days.

### Step 2: Update `GET /timesheets/for-period/{id}` — Allow Closed Periods in Grace Window

**File:** `backend/app/api/timesheets.py`

Currently rejects `status != "open"` with a hard 400. Change to allow closed periods that are within the grace window.

```python
GRACE_PERIOD_DAYS = 7

# Replace the hard status check:
if pay_period.status == "processed":
    raise HTTPException(status_code=400, detail="Pay period has been processed")

if pay_period.status == "closed":
    grace_cutoff = today - timedelta(days=GRACE_PERIOD_DAYS)
    if pay_period.end_date < grace_cutoff:
        raise HTTPException(
            status_code=400,
            detail="Pay period is closed and past the grace period for late entries",
        )
```

This means: `open` always allowed, `closed` allowed if `end_date >= today - 7`, `processed` always blocked.

### Step 3: No Changes to Entry Create/Update Endpoints

The `create_time_entry` and `create_pto_entry` endpoints only check **timesheet status** (`draft`/`rejected`), not pay period status. Once the user can reach a draft timesheet for the closed period (via Step 2), entry creation already works. No changes needed.

Similarly, `update_time_entry`, `update_pto_entry`, and the delete endpoints only check timesheet status. No changes needed.

### Step 4: Frontend — Show Grace Period Context in Pay Period Selector

**Files:** `frontend/src/pages/TimeEntry.tsx`, `frontend/src/pages/PTOEntry.tsx`

In the pay period selector (already implemented), add a visual indicator for closed-but-in-grace periods so the user understands the window is limited:

- Open periods: show as normal (with "Current" badge if applicable)
- Closed-in-grace periods: show with a subtle warning label like "Closes for entries in X days"

No other frontend changes needed — the selector, date picker, and form submission already work correctly once the backend returns the period and allows timesheet access.

### Step 5: Define Grace Period as a Constant

**File:** `backend/app/core/config.py` (or a new constants file)

Define `GRACE_PERIOD_DAYS = 7` in one place and import it in both `pay_periods.py` and `timesheets.py`. This makes it easy to adjust later (e.g., change from 7 to 14 days).

### Step 6: Update Dashboard Past Timesheets Section

**File:** `frontend/src/pages/Dashboard.tsx`

The "Past Timesheets Needing Attention" section (already implemented) will automatically pick up closed-in-grace timesheets because it reads from `getRecentPayPeriods()` which now includes them. No additional changes needed — timesheets from grace-window periods will appear if they are in `draft` or `rejected` status.

## Files to Modify

| File | Change |
|------|--------|
| `backend/app/api/pay_periods.py` | Update `GET /recent` to include closed periods in grace window |
| `backend/app/api/timesheets.py` | Update `GET /for-period/{id}` to allow closed periods in grace window |
| `frontend/src/pages/TimeEntry.tsx` | Add grace period label to period selector (optional UX polish) |
| `frontend/src/pages/PTOEntry.tsx` | Same grace period label (optional UX polish) |

## Files NOT to Modify

- `backend/app/models/pay_period.py` — No model changes, no new columns
- `backend/app/schemas/` — No schema changes
- `create_time_entry` / `create_pto_entry` endpoints — Already only check timesheet status
- `update_time_entry` / `update_pto_entry` endpoints — Same
- `frontend/src/timesheetStatus.ts` — `getEntryDateMax()` works correctly for past periods
- `frontend/src/services/api.ts` — `getRecentPayPeriods()` and `getTimesheetForPeriod()` already exist
- `frontend/src/pages/TimesheetDetail.tsx` — Already works via `?timesheet=<id>`

## UX Flow After Implementation

### Employee forgot to log time for a closed period (grace window):
1. User taps "Add Time" on Dashboard
2. Pay period selector shows current period AND the recently-closed period (labeled "Closes for entries in 3 days")
3. User selects the closed period
4. Date picker shows that period's valid date range
5. User fills out entry and saves — works normally
6. Entry is saved to the draft timesheet for the closed period

### Employee tries to add time for a period past the grace window:
1. Period does not appear in the selector at all
2. If somehow accessed directly, backend returns: "Pay period is closed and past the grace period for late entries"

### Admin workflow unchanged:
- Admin closes pay periods as usual
- Employees still have 7 days to finish entering time
- After 7 days, the period is fully locked
- `processed` status remains a hard lock at all times (for payroll finalization)

## Testing

- Backend: Verify `GET /recent` returns closed periods within grace window
- Backend: Verify `GET /recent` excludes closed periods outside grace window
- Backend: Verify `GET /for-period/{id}` allows closed period within grace
- Backend: Verify `GET /for-period/{id}` rejects closed period outside grace
- Backend: Verify `GET /for-period/{id}` always rejects `processed` periods
- Backend: Verify `create_time_entry` works on draft timesheet for closed-in-grace period
- Frontend: Verify closed-in-grace periods appear in selector
- Frontend: Verify date picker bounds correct for closed period
- Frontend: Verify entry saves correctly to closed-period timesheet

## Configuration

The grace period is controlled by a single constant: `GRACE_PERIOD_DAYS = 7`. To change the grace window, update this value. Reasonable range: 3-14 days depending on business needs.
