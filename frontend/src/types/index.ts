export interface Company {
  id: string
  name: string
  slug: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface User {
  id: string
  email: string
  first_name: string
  last_name: string
  full_name: string
  hire_date: string
  pay_period_group: string
  hourly_rate?: number
  is_manager: boolean
  is_admin: boolean
  is_super_admin: boolean
  is_active: boolean
  company_id: string
}

export interface Client {
  id: string
  name: string
  industry: string | null
  quickbooks_customer_id: string | null
  is_active: boolean
}

export interface ServiceType {
  id: string
  name: string
  is_billable: boolean
}

export interface Location {
  id: string
  client_id: string
  region: string | null
  site_name: string
  is_active: boolean
}

export interface JobCode {
  id: string
  location_id: string
  code: string
  description: string | null
  quickbooks_class_id: string | null
  is_active: boolean
}

export interface PayPeriod {
  id: string
  period_group: string
  start_date: string
  end_date: string
  payroll_run_date: string | null
  status: 'open' | 'closed' | 'processed'
}

export interface Timesheet {
  id: string
  employee_id: string
  pay_period_id: string
  status: 'draft' | 'submitted' | 'approved' | 'rejected'
  submitted_at: string | null
  approved_at: string | null
  approved_by: string | null
  rejection_reason: string | null
  employee_name: string | null
  created_at: string
  updated_at: string
}

export interface BillingWeek {
  id: string
  timesheet_id: string
  week_start_date: string
  week_end_date: string
  status: 'open' | 'submitted' | 'approved' | 'billed' | 'reopened'
  submitted_at: string | null
  approved_at: string | null
  approved_by: string | null
  billed_at: string | null
  created_at: string
  updated_at: string
}

export interface TimeEntry {
  id: string
  timesheet_id: string
  work_date: string
  client_id: string | null
  location_id: string | null
  job_code_id: string | null
  service_type_id: string | null
  work_mode: 'remote' | 'on_site'
  hours: number
  start_time: string | null
  end_time: string | null
  description: string | null
  is_billable: boolean
  is_overtime: boolean
  vehicle_reimbursement_tier: string | null
  created_at: string
  updated_at: string
}

export interface PTOEntry {
  id: string
  timesheet_id: string
  pto_date: string
  pto_type: 'personal' | 'sick' | 'holiday' | 'other'
  hours: number
  notes: string | null
}

export interface SiteRequest {
  id: string
  employee_id: string
  client_id: string
  site_name: string
  region: string | null
  job_code: string | null
  job_code_description: string | null
  notes: string | null
  status: 'pending' | 'approved' | 'rejected'
  reviewed_by: string | null
  reviewed_at: string | null
  rejection_reason: string | null
  created_location_id: string | null
  created_job_code_id: string | null
  employee_name: string | null
  client_name: string | null
  reviewer_name: string | null
  created_at: string
  updated_at: string
}

export interface SiteRequestCreate {
  client_id: string
  site_name: string
  region?: string
  job_code?: string
  job_code_description?: string
  notes?: string
}

export interface TimeEntryCreate {
  work_date: string
  client_id?: string
  location_id?: string
  job_code_id?: string
  service_type_id?: string
  work_mode: 'remote' | 'on_site'
  hours: number
  start_time?: string
  end_time?: string
  description?: string
  is_billable?: boolean
  is_overtime?: boolean
  vehicle_reimbursement_tier?: string
}
