import type { User, Company, Client, ServiceType, PayPeriod, Timesheet, BillingWeek, TimeEntry, PTOEntry, TimeEntryCreate, Location, JobCode, SiteRequest, SiteRequestCreate } from '../types'

const API_BASE = '/api'

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
    this.name = 'ApiError'
  }
}

async function fetchApi<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = localStorage.getItem('token')

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  }

  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  })

  if (!response.ok) {
    if (response.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }

    const error = await response.json().catch(() => ({ detail: 'An error occurred' }))
    const detail = error.detail
    const message = typeof detail === 'string'
      ? detail
      : Array.isArray(detail)
        ? detail.map((d: any) => d.msg || JSON.stringify(d)).join('; ')
        : 'An error occurred'
    throw new ApiError(response.status, message)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return response.json()
}

async function fetchApiBlob(
  endpoint: string,
  options: RequestInit = {}
): Promise<Blob> {
  const token = localStorage.getItem('token')

  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  }

  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  })

  if (!response.ok) {
    if (response.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }

    const err = await response
      .json()
      .catch(() => ({ detail: 'An error occurred' }))
    throw new ApiError(response.status, err.detail || 'An error occurred')
  }

  return response.blob()
}

// Auth
export async function login(email: string, password: string): Promise<{ access_token: string }> {
  const formData = new URLSearchParams()
  formData.append('username', email)
  formData.append('password', password)

  const response = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: formData,
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Login failed' }))
    throw new ApiError(response.status, error.detail)
  }

  return response.json()
}

export async function getCurrentUser(): Promise<User> {
  return fetchApi<User>('/auth/me')
}

// Companies (super-admin only)
export async function getCompanies(activeOnly = true): Promise<Company[]> {
  return fetchApi<Company[]>(`/companies?active_only=${activeOnly}`)
}

export async function getCompany(id: string): Promise<Company> {
  return fetchApi<Company>(`/companies/${id}`)
}

export async function createCompany(data: { name: string; slug: string; is_active?: boolean }): Promise<Company> {
  return fetchApi<Company>('/companies', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateCompany(id: string, data: Partial<{ name: string; slug: string; is_active: boolean }>): Promise<Company> {
  return fetchApi<Company>(`/companies/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

export async function deleteCompany(id: string): Promise<void> {
  return fetchApi<void>(`/companies/${id}`, { method: 'DELETE' })
}

// Clients
export async function getClients(companyId?: string): Promise<Client[]> {
  const params = companyId ? `?company_id=${companyId}` : ''
  return fetchApi<Client[]>(`/clients${params}`)
}

export async function getAllClients(companyId?: string): Promise<Client[]> {
  const qs = new URLSearchParams({ active_only: 'false' })
  if (companyId) qs.set('company_id', companyId)
  return fetchApi<Client[]>(`/clients?${qs}`)
}

export async function createClient(data: { name: string; industry?: string; is_active?: boolean }): Promise<Client> {
  return fetchApi<Client>('/clients', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateClient(id: string, data: Partial<{ name: string; industry: string | null; is_active: boolean }>): Promise<Client> {
  return fetchApi<Client>(`/clients/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

export async function deleteClient(id: string): Promise<void> {
  return fetchApi<void>(`/clients/${id}`, { method: 'DELETE' })
}

// Service Types
export async function getServiceTypes(companyId?: string): Promise<ServiceType[]> {
  const params = companyId ? `?company_id=${companyId}` : ''
  return fetchApi<ServiceType[]>(`/service-types${params}`)
}

export async function createServiceType(data: { name: string; is_billable?: boolean }): Promise<ServiceType> {
  return fetchApi<ServiceType>('/service-types', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateServiceType(id: string, data: Partial<{ name: string; is_billable: boolean }>): Promise<ServiceType> {
  return fetchApi<ServiceType>(`/service-types/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

export async function deleteServiceType(id: string): Promise<void> {
  return fetchApi<void>(`/service-types/${id}`, { method: 'DELETE' })
}

// Pay Periods
export async function getCurrentPayPeriod(): Promise<PayPeriod> {
  return fetchApi<PayPeriod>('/pay-periods/current')
}

export async function getPayPeriod(id: string): Promise<PayPeriod> {
  return fetchApi<PayPeriod>(`/pay-periods/${id}`)
}

export async function getPayPeriods(limit = 10, companyId?: string): Promise<PayPeriod[]> {
  const qs = new URLSearchParams({ limit: String(limit) })
  if (companyId) qs.set('company_id', companyId)
  return fetchApi<PayPeriod[]>(`/pay-periods?${qs}`)
}

export async function getAllPayPeriods(params?: { period_group?: string; status_filter?: string; limit?: number; company_id?: string }): Promise<PayPeriod[]> {
  const searchParams = new URLSearchParams()
  if (params?.period_group) searchParams.append('period_group', params.period_group)
  if (params?.status_filter) searchParams.append('status_filter', params.status_filter)
  if (params?.company_id) searchParams.append('company_id', params.company_id)
  searchParams.append('limit', String(params?.limit || 50))
  return fetchApi<PayPeriod[]>(`/pay-periods?${searchParams.toString()}`)
}

export async function createPayPeriod(data: { period_group: string; start_date: string; end_date: string; payroll_run_date?: string }): Promise<PayPeriod> {
  return fetchApi<PayPeriod>('/pay-periods', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function generatePayPeriods(data: { start_date: string; weeks?: number; period_group?: string }): Promise<PayPeriod[]> {
  const params = new URLSearchParams({ start_date: data.start_date })
  if (data.weeks) params.append('weeks', String(data.weeks))
  if (data.period_group) params.append('period_group', data.period_group)
  return fetchApi<PayPeriod[]>(`/pay-periods/generate?${params.toString()}`, {
    method: 'POST',
  })
}

export async function updatePayPeriod(id: string, data: Partial<{ start_date: string; end_date: string; payroll_run_date: string | null; status: string }>): Promise<PayPeriod> {
  return fetchApi<PayPeriod>(`/pay-periods/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

export async function closePayPeriod(id: string): Promise<PayPeriod> {
  return fetchApi<PayPeriod>(`/pay-periods/${id}/close`, { method: 'POST' })
}

export async function getRecentPayPeriods(): Promise<PayPeriod[]> {
  return fetchApi<PayPeriod[]>('/pay-periods/recent')
}

// Timesheets
export async function getCurrentTimesheet(): Promise<Timesheet> {
  return fetchApi<Timesheet>('/timesheets/current')
}

export async function getTimesheetForPeriod(payPeriodId: string): Promise<Timesheet> {
  return fetchApi<Timesheet>(`/timesheets/for-period/${payPeriodId}`)
}

export async function getTimesheets(params?: { status?: string; employee_id?: string; pay_period_id?: string; company_id?: string }): Promise<Timesheet[]> {
  const searchParams = new URLSearchParams()
  if (params?.status) searchParams.append('status_filter', params.status)
  if (params?.employee_id) searchParams.append('employee_id', params.employee_id)
  if (params?.pay_period_id) searchParams.append('pay_period_id', params.pay_period_id)
  if (params?.company_id) searchParams.append('company_id', params.company_id)

  const query = searchParams.toString()
  return fetchApi<Timesheet[]>(`/timesheets${query ? `?${query}` : ''}`)
}

export async function getTimesheet(id: string): Promise<Timesheet> {
  return fetchApi<Timesheet>(`/timesheets/${id}`)
}

export async function submitTimesheet(id: string): Promise<Timesheet> {
  return fetchApi<Timesheet>(`/timesheets/${id}/submit`, {
    method: 'POST',
  })
}

export async function approveTimesheet(id: string): Promise<Timesheet> {
  return fetchApi<Timesheet>(`/timesheets/${id}/approve`, {
    method: 'POST',
  })
}

export async function deleteTimesheet(id: string): Promise<void> {
  return fetchApi<void>(`/timesheets/${id}`, {
    method: 'DELETE',
  })
}

export async function reopenTimesheet(id: string): Promise<Timesheet> {
  return fetchApi<Timesheet>(`/timesheets/${id}/reopen`, {
    method: 'POST',
  })
}

export async function rejectTimesheet(id: string, reason: string): Promise<Timesheet> {
  return fetchApi<Timesheet>(
    `/timesheets/${id}/reject`,
    {
      method: 'POST',
      body: JSON.stringify({ rejection_reason: reason }),
    }
  )
}

// Billing weeks
export async function getBillingWeeks(timesheetId: string): Promise<BillingWeek[]> {
  return fetchApi<BillingWeek[]>(`/timesheets/${timesheetId}/billing-weeks`)
}

export async function submitBillingWeek(timesheetId: string, weekId: string): Promise<BillingWeek> {
  return fetchApi<BillingWeek>(`/timesheets/${timesheetId}/billing-weeks/${weekId}/submit`, {
    method: 'POST',
  })
}

export async function approveBillingWeek(timesheetId: string, weekId: string): Promise<BillingWeek> {
  return fetchApi<BillingWeek>(`/timesheets/${timesheetId}/billing-weeks/${weekId}/approve`, {
    method: 'POST',
  })
}

export async function reopenBillingWeek(timesheetId: string, weekId: string): Promise<BillingWeek> {
  return fetchApi<BillingWeek>(`/timesheets/${timesheetId}/billing-weeks/${weekId}/reopen`, {
    method: 'POST',
  })
}

export async function markBilledBillingWeek(timesheetId: string, weekId: string): Promise<BillingWeek> {
  return fetchApi<BillingWeek>(`/timesheets/${timesheetId}/billing-weeks/${weekId}/mark-billed`, {
    method: 'POST',
  })
}

// Time Entries
export async function getTimeEntries(timesheetId: string): Promise<TimeEntry[]> {
  return fetchApi<TimeEntry[]>(`/timesheets/${timesheetId}/entries`)
}

export async function createTimeEntry(
  timesheetId: string,
  data: TimeEntryCreate
): Promise<TimeEntry> {
  return fetchApi<TimeEntry>(`/timesheets/${timesheetId}/entries`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateTimeEntry(
  timesheetId: string,
  entryId: string,
  data: Partial<TimeEntryCreate>
): Promise<TimeEntry> {
  return fetchApi<TimeEntry>(
    `/timesheets/${timesheetId}/entries/${entryId}`,
    {
      method: 'PATCH',
      body: JSON.stringify(data),
    }
  )
}

export async function deleteTimeEntry(timesheetId: string, entryId: string): Promise<void> {
  return fetchApi<void>(`/timesheets/${timesheetId}/entries/${entryId}`, {
    method: 'DELETE',
  })
}

// PTO Entries
export async function getPTOEntries(timesheetId: string): Promise<PTOEntry[]> {
  return fetchApi<PTOEntry[]>(`/timesheets/${timesheetId}/pto`)
}

export async function createPTOEntry(
  timesheetId: string,
  data: { pto_date: string; pto_type: string; hours: number; notes?: string }
): Promise<PTOEntry> {
  return fetchApi<PTOEntry>(`/timesheets/${timesheetId}/pto`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

// Employees (for managers)
export async function getEmployees(companyId?: string): Promise<User[]> {
  const params = companyId ? `?company_id=${companyId}` : ''
  return fetchApi<User[]>(`/employees${params}`)
}

export async function createEmployee(data: {
  email: string
  password: string
  first_name: string
  last_name: string
  hire_date: string
  pay_period_group: string
  hourly_rate?: number
  is_manager?: boolean
  is_admin?: boolean
}): Promise<User> {
  return fetchApi<User>('/employees', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateEmployee(
  id: string,
  data: Partial<{
    email: string
    first_name: string
    last_name: string
    pay_period_group: string
    hourly_rate: number
    is_manager: boolean
    is_admin: boolean
    is_active: boolean
  }>
): Promise<User> {
  return fetchApi<User>(`/employees/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

// Locations
export async function getLocations(clientId?: string): Promise<Location[]> {
  const params = clientId ? `?client_id=${clientId}` : ''
  return fetchApi<Location[]>(`/locations${params}`)
}

export async function getAllLocations(clientId?: string): Promise<Location[]> {
  const params = new URLSearchParams({ active_only: 'false' })
  if (clientId) params.append('client_id', clientId)
  return fetchApi<Location[]>(`/locations?${params.toString()}`)
}

export async function createLocation(data: {
  client_id: string
  site_name: string
  region?: string
  site_code?: string | null
  latitude?: number | null
  longitude?: number | null
  is_active?: boolean
}): Promise<Location> {
  return fetchApi<Location>('/locations', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateLocation(
  id: string,
  data: Partial<{
    site_name: string
    region: string | null
    site_code: string | null
    latitude: number | null
    longitude: number | null
    is_active: boolean
  }>,
): Promise<Location> {
  return fetchApi<Location>(`/locations/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

// Job Codes
export async function getJobCodes(locationId: string): Promise<JobCode[]> {
  return fetchApi<JobCode[]>(`/locations/${locationId}/job-codes`)
}

export async function createJobCode(locationId: string, data: { code: string; description?: string }): Promise<JobCode> {
  return fetchApi<JobCode>(`/locations/${locationId}/job-codes`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function deleteLocation(locationId: string): Promise<void> {
  return fetchApi<void>(`/locations/${locationId}`, { method: 'DELETE' })
}

export async function deleteJobCode(locationId: string, jobCodeId: string): Promise<void> {
  return fetchApi<void>(`/locations/${locationId}/job-codes/${jobCodeId}`, { method: 'DELETE' })
}

// Reports
export async function getPayrollReport(payPeriodId: string, companyId?: string): Promise<Blob> {
  const qs = new URLSearchParams({ pay_period_id: payPeriodId, format: 'csv' })
  if (companyId) qs.set('company_id', companyId)
  return fetchApiBlob(`/reports/payroll?${qs}`)
}

export async function getBillingReport(startDate?: string, endDate?: string, companyId?: string): Promise<Blob> {
  const qs = new URLSearchParams({ format: 'csv' })
  if (startDate) qs.set('start_date', startDate)
  if (endDate) qs.set('end_date', endDate)
  if (companyId) qs.set('company_id', companyId)
  return fetchApiBlob(`/reports/billing?${qs}`)
}

export async function getEngageExport(payPeriodId: string, companyId?: string): Promise<Blob> {
  const qs = new URLSearchParams({ pay_period_id: payPeriodId })
  if (companyId) qs.set('company_id', companyId)
  return fetchApiBlob(`/reports/engage-export?${qs}`)
}

export async function getEmployeeDetailReport(params: {
  employeeIds: string[]
  startDate: string
  endDate: string
  timesheetStatus?: string
  payPeriodStatus?: string
  includePto?: boolean
  format?: string
  companyId?: string
}): Promise<Blob> {
  const fmt = params.format || 'csv'
  const qs = new URLSearchParams({
    employee_ids: params.employeeIds.join(','),
    start_date: params.startDate,
    end_date: params.endDate,
    format: fmt,
    include_pto: String(params.includePto ?? true),
  })
  if (params.timesheetStatus) qs.set('timesheet_status', params.timesheetStatus)
  if (params.payPeriodStatus && params.payPeriodStatus !== 'all') {
    qs.set('pay_period_status', params.payPeriodStatus)
  }
  if (params.companyId) qs.set('company_id', params.companyId)
  return fetchApiBlob(`/reports/employee-detail?${qs}`)
}

export async function getMyTimeDetailReport(params: {
  startDate: string
  endDate: string
  timesheetStatus?: string
  payPeriodStatus?: string
  includePto?: boolean
  format?: string
}): Promise<Blob> {
  const fmt = params.format || 'csv'
  const qs = new URLSearchParams({
    start_date: params.startDate,
    end_date: params.endDate,
    format: fmt,
    include_pto: String(params.includePto ?? true),
  })
  if (params.timesheetStatus) qs.set('timesheet_status', params.timesheetStatus)
  if (params.payPeriodStatus && params.payPeriodStatus !== 'all') {
    qs.set('pay_period_status', params.payPeriodStatus)
  }
  return fetchApiBlob(`/reports/my-time-detail?${qs}`)
}

export async function getBiweeklyPayrollReport(params: {
  periodGroup: string
  anchorStartDate: string
  format?: string
  companyId?: string
}): Promise<Blob> {
  const fmt = params.format || 'csv'
  const qs = new URLSearchParams({
    period_group: params.periodGroup,
    anchor_start_date: params.anchorStartDate,
    format: fmt,
  })
  if (params.companyId) qs.set('company_id', params.companyId)
  return fetchApiBlob(`/reports/payroll-biweekly?${qs}`)
}

// Update PTO entry
export async function updatePTOEntry(
  timesheetId: string,
  entryId: string,
  data: { pto_date?: string; pto_type?: string; hours?: number; notes?: string }
): Promise<PTOEntry> {
  return fetchApi<PTOEntry>(`/timesheets/${timesheetId}/pto/${entryId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

// Delete PTO entry
export async function deletePTOEntry(timesheetId: string, entryId: string): Promise<void> {
  return fetchApi<void>(`/timesheets/${timesheetId}/pto/${entryId}`, {
    method: 'DELETE',
  })
}

// Site Requests
export async function getSiteRequests(status?: string): Promise<SiteRequest[]> {
  const params = status ? `?status_filter=${status}` : ''
  return fetchApi<SiteRequest[]>(`/site-requests${params}`)
}

export async function createSiteRequest(data: SiteRequestCreate): Promise<SiteRequest> {
  return fetchApi<SiteRequest>('/site-requests', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function approveSiteRequest(id: string): Promise<SiteRequest> {
  return fetchApi<SiteRequest>(`/site-requests/${id}/approve`, {
    method: 'POST',
  })
}

export async function rejectSiteRequest(id: string, reason: string): Promise<SiteRequest> {
  return fetchApi<SiteRequest>(`/site-requests/${id}/reject`, {
    method: 'POST',
    body: JSON.stringify({ rejection_reason: reason }),
  })
}

export async function deleteSiteRequest(id: string): Promise<void> {
  await fetchApi(`/site-requests/${id}`, { method: 'DELETE' })
}

// Admin reset password
export async function adminResetPassword(employeeId: string, newPassword: string): Promise<{ message: string }> {
  return fetchApi<{ message: string }>(
    `/auth/admin-reset-password`,
    {
      method: 'POST',
      body: JSON.stringify({ employee_id: employeeId, new_password: newPassword }),
    }
  )
}

// Change password
export async function changePassword(currentPassword: string, newPassword: string): Promise<{ message: string }> {
  return fetchApi<{ message: string }>(
    `/auth/change-password`,
    {
      method: 'POST',
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
    }
  )
}

// Request password reset
export async function requestPasswordReset(email: string): Promise<{ message: string }> {
  const response = await fetch(`${API_BASE}/auth/request-reset`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  })
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }))
    throw new ApiError(response.status, error.detail)
  }
  return response.json()
}

// === Report JSON Preview APIs ===
import type {
  PayrollReport,
  BillingReport,
  BiweeklyReport,
  DetailReport,
  HoursByEmployeeReport,
  HoursBySiteCodeReport,
} from '../types/reports'

export async function previewMyTimeDetail(params: {
  startDate: string
  endDate: string
  timesheetStatus?: string
  payPeriodStatus?: string
  includePto?: boolean
}): Promise<DetailReport> {
  const qs = new URLSearchParams({
    start_date: params.startDate,
    end_date: params.endDate,
    format: 'json',
    include_pto: String(params.includePto ?? true),
  })
  if (params.timesheetStatus) qs.set('timesheet_status', params.timesheetStatus)
  if (params.payPeriodStatus && params.payPeriodStatus !== 'all') qs.set('pay_period_status', params.payPeriodStatus)
  return fetchApi<DetailReport>(`/reports/my-time-detail?${qs}`)
}

export async function previewEmployeeDetail(params: {
  employeeIds: string[]
  startDate: string
  endDate: string
  timesheetStatus?: string
  payPeriodStatus?: string
  includePto?: boolean
  companyId?: string
}): Promise<DetailReport> {
  const qs = new URLSearchParams({
    employee_ids: params.employeeIds.join(','),
    start_date: params.startDate,
    end_date: params.endDate,
    format: 'json',
    include_pto: String(params.includePto ?? true),
  })
  if (params.timesheetStatus) qs.set('timesheet_status', params.timesheetStatus)
  if (params.payPeriodStatus && params.payPeriodStatus !== 'all') qs.set('pay_period_status', params.payPeriodStatus)
  if (params.companyId) qs.set('company_id', params.companyId)
  return fetchApi<DetailReport>(`/reports/employee-detail?${qs}`)
}

export async function previewPayroll(payPeriodId: string, companyId?: string): Promise<PayrollReport> {
  const qs = new URLSearchParams({ pay_period_id: payPeriodId, format: 'json' })
  if (companyId) qs.set('company_id', companyId)
  return fetchApi<PayrollReport>(`/reports/payroll?${qs}`)
}

export async function previewBilling(startDate?: string, endDate?: string, companyId?: string): Promise<BillingReport> {
  const qs = new URLSearchParams({ format: 'json' })
  if (startDate) qs.set('start_date', startDate)
  if (endDate) qs.set('end_date', endDate)
  if (companyId) qs.set('company_id', companyId)
  return fetchApi<BillingReport>(`/reports/billing?${qs}`)
}

export async function previewBiweekly(params: {
  periodGroup: string
  anchorStartDate: string
  companyId?: string
}): Promise<BiweeklyReport> {
  const qs = new URLSearchParams({
    period_group: params.periodGroup,
    anchor_start_date: params.anchorStartDate,
    format: 'json',
  })
  if (params.companyId) qs.set('company_id', params.companyId)
  return fetchApi<BiweeklyReport>(`/reports/payroll-biweekly?${qs}`)
}

export async function getHoursByEmployeeReport(startDate?: string, endDate?: string, companyId?: string, fmt = 'csv'): Promise<Blob> {
  const qs = new URLSearchParams({ format: fmt })
  if (startDate) qs.set('start_date', startDate)
  if (endDate) qs.set('end_date', endDate)
  if (companyId) qs.set('company_id', companyId)
  return fetchApiBlob(`/reports/hours-by-employee?${qs}`)
}

export async function getHoursBySiteCodeReport(params: {
  startDate?: string; endDate?: string; clientId?: string; companyId?: string; format?: string
}): Promise<Blob> {
  const fmt = params.format || 'csv'
  const qs = new URLSearchParams({ format: fmt })
  if (params.startDate) qs.set('start_date', params.startDate)
  if (params.endDate) qs.set('end_date', params.endDate)
  if (params.clientId) qs.set('client_id', params.clientId)
  if (params.companyId) qs.set('company_id', params.companyId)
  return fetchApiBlob(`/reports/hours-by-job-code?${qs}`)
}

export async function previewHoursByEmployee(startDate?: string, endDate?: string, companyId?: string): Promise<HoursByEmployeeReport> {
  const qs = new URLSearchParams({ format: 'json' })
  if (startDate) qs.set('start_date', startDate)
  if (endDate) qs.set('end_date', endDate)
  if (companyId) qs.set('company_id', companyId)
  return fetchApi<HoursByEmployeeReport>(`/reports/hours-by-employee?${qs}`)
}

export async function previewHoursBySiteCode(params: {
  startDate?: string; endDate?: string; clientId?: string; companyId?: string
}): Promise<HoursBySiteCodeReport> {
  const qs = new URLSearchParams({ format: 'json' })
  if (params.startDate) qs.set('start_date', params.startDate)
  if (params.endDate) qs.set('end_date', params.endDate)
  if (params.clientId) qs.set('client_id', params.clientId)
  if (params.companyId) qs.set('company_id', params.companyId)
  return fetchApi<HoursBySiteCodeReport>(`/reports/hours-by-job-code?${qs}`)
}

// Reset password with token
export async function resetPassword(token: string, newPassword: string): Promise<{ message: string }> {
  const response = await fetch(
    `${API_BASE}/auth/reset-password`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token, new_password: newPassword }),
    }
  )
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Reset failed' }))
    throw new ApiError(response.status, error.detail)
  }
  return response.json()
}
