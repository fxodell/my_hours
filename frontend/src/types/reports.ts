// === Payroll Report ===
export interface PayrollRow {
  employee_id: string
  employee_name: string
  employee_email: string
  engage_employee_id: string | null
  pay_period_start: string
  pay_period_end: string
  period_group: string
  regular_hours: number
  overtime_hours: number
  total_work_hours: number
  personal_pto_hours: number
  sick_pto_hours: number
  holiday_hours: number
  other_pto_hours: number
  total_pto_hours: number
  total_hours: number
  approved_at: string | null
}

export interface PayrollReport {
  report: 'payroll'
  data: PayrollRow[]
}

// === Billing Report ===
export interface BillingRow {
  date: string
  client: string
  location: string
  site_code: string
  employee: string
  service_type: string
  hours: number
  work_mode: string
  description: string
}

export interface BillingReport {
  report: 'billing'
  summary: Record<string, { hours: number; bonus_hours: number }>
  data: BillingRow[]
}

// === Biweekly Payroll Report ===
export interface BiweeklyRow {
  employee_id: string
  employee_name: string
  employee_email: string
  engage_id: string | null
  period_group: string
  biweekly_start: string
  biweekly_end: string
  weeks_count: number
  missing_weeks: number[]
  regular_hours: number
  overtime_hours: number
  total_work_hours: number
  personal_pto_hours: number
  sick_pto_hours: number
  holiday_hours: number
  other_pto_hours: number
  total_pto_hours: number
  total_hours: number
  period_total_hours: number
  hours_by_date: Record<string, number>
}

export interface BiweeklyReport {
  report: 'payroll_biweekly'
  period_group: string
  biweekly_start: string
  biweekly_end: string
  week_1_pay_period_id: string
  week_2_pay_period_id: string
  data: BiweeklyRow[]
  data_quality_warnings?: string[]
}

// === Detail Report (employee-detail and my-time-detail) ===
export interface DetailRow {
  entry_kind: 'work' | 'pto'
  work_date: string
  employee_id: string
  employee_name: string
  client: string
  location: string
  region: string
  site_code: string
  job_code_description: string
  service_type: string
  work_mode: string
  hours: number
  description: string
  is_billable: boolean
  is_overtime: boolean
  start_time: string
  end_time: string
  vehicle_reimbursement_tier: string
  pto_type: string
  timesheet_id: string
  timesheet_status: string
  pay_period_start: string
  pay_period_end: string
  period_group: string
}

export interface DetailSummaryRow {
  employee_id: string
  employee_name: string
  total_work_hours: number
  total_pto_hours: number
  total_hours: number
}

export interface DetailReport {
  report: 'employee_detail' | 'my_time_detail'
  start_date: string
  end_date: string
  row_count: number
  summary: DetailSummaryRow[]
  grand_total: {
    total_work_hours: number
    total_pto_hours: number
    total_hours: number
  }
  data: DetailRow[]
}

// === Hours by Job Code ===
export interface HoursByJobCodeRow {
  client: string
  service_type: string
  job_code: string
  total_hours: number
}

export interface HoursByJobCodeReport {
  report: 'hours_by_job_code'
  data: HoursByJobCodeRow[]
}

// === Hours by Employee ===
export interface HoursByEmployeeRow {
  employee_id: string
  employee_name: string
  email: string
  total_hours: number
}

export interface HoursByEmployeeReport {
  report: 'hours_by_employee'
  data: HoursByEmployeeRow[]
}
