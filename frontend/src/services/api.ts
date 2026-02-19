import type { User, Client, ServiceType, PayPeriod, Timesheet, TimeEntry, PTOEntry, TimeEntryCreate, Location, JobCode } from '../types'

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
    throw new ApiError(response.status, error.detail || 'An error occurred')
  }

  if (response.status === 204) {
    return undefined as T
  }

  return response.json()
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

// Clients
export async function getClients(): Promise<Client[]> {
  return fetchApi<Client[]>('/clients')
}

// Service Types
export async function getServiceTypes(): Promise<ServiceType[]> {
  return fetchApi<ServiceType[]>('/service-types')
}

// Pay Periods
export async function getCurrentPayPeriod(): Promise<PayPeriod> {
  return fetchApi<PayPeriod>('/pay-periods/current')
}

export async function getPayPeriods(limit = 10): Promise<PayPeriod[]> {
  return fetchApi<PayPeriod[]>(`/pay-periods?limit=${limit}`)
}

// Timesheets
export async function getCurrentTimesheet(): Promise<Timesheet> {
  return fetchApi<Timesheet>('/timesheets/current')
}

export async function getTimesheets(params?: { status?: string; employee_id?: string }): Promise<Timesheet[]> {
  const searchParams = new URLSearchParams()
  if (params?.status) searchParams.append('status_filter', params.status)
  if (params?.employee_id) searchParams.append('employee_id', params.employee_id)

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
    `/timesheets/${id}/reject?rejection_reason=${encodeURIComponent(reason)}`,
    { method: 'POST' }
  )
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
export async function getEmployees(): Promise<User[]> {
  return fetchApi<User[]>('/employees')
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

// Job Codes
export async function getJobCodes(locationId: string): Promise<JobCode[]> {
  return fetchApi<JobCode[]>(`/locations/${locationId}/job-codes`)
}

// Reports
export async function getPayrollReport(payPeriodId: string): Promise<Blob> {
  const token = localStorage.getItem('token')
  const response = await fetch(`/api/reports/payroll?pay_period_id=${payPeriodId}&format=csv`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!response.ok) throw new Error('Failed to download report')
  return response.blob()
}

export async function getBillingReport(payPeriodId: string): Promise<Blob> {
  const token = localStorage.getItem('token')
  const response = await fetch(`/api/reports/billing?pay_period_id=${payPeriodId}&format=csv`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!response.ok) throw new Error('Failed to download report')
  return response.blob()
}

export async function getEngageExport(payPeriodId: string): Promise<Blob> {
  const token = localStorage.getItem('token')
  const response = await fetch(`/api/reports/engage-export?pay_period_id=${payPeriodId}`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!response.ok) throw new Error('Failed to download Engage export')
  return response.blob()
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

// Change password
export async function changePassword(currentPassword: string, newPassword: string): Promise<{ message: string }> {
  return fetchApi<{ message: string }>(
    `/auth/change-password?current_password=${encodeURIComponent(currentPassword)}&new_password=${encodeURIComponent(newPassword)}`,
    { method: 'POST' }
  )
}

// Request password reset
export async function requestPasswordReset(email: string): Promise<{ message: string }> {
  const response = await fetch(`${API_BASE}/auth/request-reset?email=${encodeURIComponent(email)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  })
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }))
    throw new ApiError(response.status, error.detail)
  }
  return response.json()
}

// Reset password with token
export async function resetPassword(token: string, newPassword: string): Promise<{ message: string }> {
  const response = await fetch(
    `${API_BASE}/auth/reset-password?token=${encodeURIComponent(token)}&new_password=${encodeURIComponent(newPassword)}`,
    { method: 'POST', headers: { 'Content-Type': 'application/json' } }
  )
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Reset failed' }))
    throw new ApiError(response.status, error.detail)
  }
  return response.json()
}
