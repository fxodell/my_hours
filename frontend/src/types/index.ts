export interface User {
  id: string
  email: string
  first_name: string
  last_name: string
  full_name: string
  hire_date: string
  pay_period_group: string
  is_manager: boolean
  is_admin: boolean
  is_active: boolean
}

export interface Client {
  id: string
  name: string
  industry: string | null
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
  is_active: boolean
}

export interface PayPeriod {
  id: string
  period_group: string
  start_date: string
  end_date: string
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
  bonus_eligible: boolean
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
  bonus_eligible?: boolean
}
