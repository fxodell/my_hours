import { format } from 'date-fns'
import type { Timesheet } from './types'

type TimesheetStatus = Timesheet['status'] | undefined

export function isTimesheetEditable(status: TimesheetStatus): boolean {
  return status === 'draft' || status === 'rejected'
}

export function isTimesheetReadOnly(status: TimesheetStatus): boolean {
  return status === 'submitted' || status === 'approved'
}

export function getEntryDateMax(endDate?: string): string | undefined {
  if (!endDate) return undefined

  const today = format(new Date(), 'yyyy-MM-dd')
  return endDate < today ? endDate : today
}
