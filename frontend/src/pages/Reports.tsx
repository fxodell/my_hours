import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { format, parseISO, subDays } from 'date-fns'
import * as api from '../services/api'
import { useAuth } from '../contexts/AuthContext'

const DownloadIcon = () => (
  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
  </svg>
)

function DownloadButton({
  label,
  onClick,
  disabled,
  loading,
  variant = 'primary',
}: {
  label: string
  onClick: () => void
  disabled: boolean
  loading: boolean
  variant?: 'primary' | 'success'
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled || loading}
      className={variant === 'success' ? 'btn-success' : 'btn-primary'}
    >
      {loading ? (
        <span className="flex items-center gap-2">
          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
          Downloading...
        </span>
      ) : (
        <span className="flex items-center gap-2">
          <DownloadIcon />
          {label}
        </span>
      )}
    </button>
  )
}

function triggerDownload(blob: Blob, filename: string) {
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  window.URL.revokeObjectURL(url)
  document.body.removeChild(a)
}

export default function Reports() {
  const { user } = useAuth()
  const isManager = user?.is_manager || user?.is_admin

  // Track multiple concurrent downloads
  const [activeDownloads, setActiveDownloads] = useState<Set<string>>(new Set())
  const [error, setError] = useState('')

  // My Time state (independent)
  const [myStartDate, setMyStartDate] = useState(format(subDays(new Date(), 30), 'yyyy-MM-dd'))
  const [myEndDate, setMyEndDate] = useState(format(new Date(), 'yyyy-MM-dd'))
  const [myStatus, setMyStatus] = useState('all')
  const [myPayPeriodStatus, setMyPayPeriodStatus] = useState<'all' | 'open' | 'closed'>('all')
  const [myFormat, setMyFormat] = useState('csv')
  const [myIncludePto, setMyIncludePto] = useState(true)

  // Employee detail state (independent, manager only)
  const [detailStartDate, setDetailStartDate] = useState(
    format(subDays(new Date(), 30), 'yyyy-MM-dd')
  )
  const [detailEndDate, setDetailEndDate] = useState(format(new Date(), 'yyyy-MM-dd'))
  const [selectedEmployees, setSelectedEmployees] = useState<string[]>([])
  const [detailStatus, setDetailStatus] = useState('all')
  const [detailPayPeriodStatus, setDetailPayPeriodStatus] = useState<'all' | 'open' | 'closed'>('all')
  const [detailFormat, setDetailFormat] = useState('csv')
  const [detailIncludePto, setDetailIncludePto] = useState(true)

  // Biweekly rollup state (independent)
  const [biweeklyGroup, setBiweeklyGroup] = useState('A')
  const [biweeklyAnchor, setBiweeklyAnchor] = useState('')
  const [biweeklyFormat, setBiweeklyFormat] = useState('csv')

  // Pay period reports state
  const [selectedPayPeriod, setSelectedPayPeriod] = useState<string>('')

  const { data: payPeriods, isLoading } = useQuery({
    queryKey: ['payPeriods'],
    queryFn: () => api.getPayPeriods(20),
  })

  const { data: employees } = useQuery({
    queryKey: ['employees'],
    queryFn: api.getEmployees,
    enabled: isManager ?? false,
  })

  const groupPeriods = payPeriods?.filter((pp) => pp.period_group === biweeklyGroup) || []

  const startDownload = (key: string) => {
    setActiveDownloads((prev) => new Set(prev).add(key))
    setError('')
  }
  const endDownload = (key: string) => {
    setActiveDownloads((prev) => {
      const next = new Set(prev)
      next.delete(key)
      return next
    })
  }
  const isDownloading = (key: string) => activeDownloads.has(key)

  const downloadPeriodReport = async (type: 'payroll' | 'billing' | 'engage') => {
    if (!selectedPayPeriod) return
    startDownload(type)
    try {
      let blob: Blob
      const pp = payPeriods?.find((p) => p.id === selectedPayPeriod)
      if (type === 'payroll') {
        blob = await api.getPayrollReport(selectedPayPeriod)
      } else if (type === 'billing') {
        blob = await api.getBillingReport(
          pp ? pp.start_date : undefined,
          pp ? pp.end_date : undefined
        )
      } else {
        blob = await api.getEngageExport(selectedPayPeriod)
      }
      triggerDownload(blob, `${type}-report-${format(new Date(), 'yyyy-MM-dd')}.csv`)
    } catch (err: any) {
      setError(err.message || 'Download failed')
    } finally {
      endDownload(type)
    }
  }

  const downloadMyTime = async () => {
    if (myStartDate && myEndDate && myStartDate > myEndDate) {
      setError('Start date must be before end date')
      return
    }
    startDownload('my-time')
    try {
      const blob = await api.getMyTimeDetailReport({
        startDate: myStartDate,
        endDate: myEndDate,
        timesheetStatus: myStatus !== 'all' ? myStatus : undefined,
        payPeriodStatus: myPayPeriodStatus,
        includePto: myIncludePto,
        format: myFormat,
      })
      const ext = myFormat === 'excel' ? 'xlsx' : myFormat
      triggerDownload(blob, `my-time-${myStartDate}-to-${myEndDate}.${ext}`)
    } catch (err: any) {
      setError(err.message || 'Download failed')
    } finally {
      endDownload('my-time')
    }
  }

  const downloadEmployeeDetail = async () => {
    if (selectedEmployees.length === 0) return
    if (detailStartDate && detailEndDate && detailStartDate > detailEndDate) {
      setError('Start date must be before end date')
      return
    }
    startDownload('employee-detail')
    try {
      const blob = await api.getEmployeeDetailReport({
        employeeIds: selectedEmployees,
        startDate: detailStartDate,
        endDate: detailEndDate,
        timesheetStatus: detailStatus !== 'all' ? detailStatus : undefined,
        payPeriodStatus: detailPayPeriodStatus,
        includePto: detailIncludePto,
        format: detailFormat,
      })
      const ext = detailFormat === 'excel' ? 'xlsx' : detailFormat
      triggerDownload(blob, `employee-detail-${detailStartDate}-to-${detailEndDate}.${ext}`)
    } catch (err: any) {
      setError(err.message || 'Download failed')
    } finally {
      endDownload('employee-detail')
    }
  }

  const downloadBiweekly = async () => {
    if (!biweeklyAnchor) return
    startDownload('biweekly')
    try {
      const blob = await api.getBiweeklyPayrollReport({
        periodGroup: biweeklyGroup,
        anchorStartDate: biweeklyAnchor,
        format: biweeklyFormat,
      })
      const ext = biweeklyFormat === 'excel' ? 'xlsx' : biweeklyFormat
      triggerDownload(blob, `biweekly-payroll-${biweeklyGroup}-${biweeklyAnchor}.${ext}`)
    } catch (err: any) {
      setError(err.message || 'Download failed')
    } finally {
      endDownload('biweekly')
    }
  }

  const toggleEmployee = (id: string) => {
    setSelectedEmployees((prev) =>
      prev.includes(id) ? prev.filter((e) => e !== id) : [...prev, id]
    )
  }

  const selectAllEmployees = () => {
    if (!employees) return
    if (selectedEmployees.length === employees.length) {
      setSelectedEmployees([])
    } else {
      setSelectedEmployees(employees.map((e) => e.id))
    }
  }

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
      </div>
    )
  }

  return (
    <div className="space-y-6 pb-4">
      <h2 className="text-xl font-bold text-gray-900">Reports</h2>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
          {error}
        </div>
      )}

      {/* ============ SECTION: My Time Export (all users) ============ */}
      <div className="card p-4 space-y-4">
        <div>
          <h3 className="font-semibold text-gray-900 text-lg">Download My Time</h3>
          <p className="text-sm text-gray-500">Export your own time entries</p>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label">Start Date</label>
            <input
              type="date"
              value={myStartDate}
              onChange={(e) => setMyStartDate(e.target.value)}
              className="input"
            />
          </div>
          <div>
            <label className="label">End Date</label>
            <input
              type="date"
              value={myEndDate}
              onChange={(e) => setMyEndDate(e.target.value)}
              className="input"
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label">Status Filter</label>
            <select value={myStatus} onChange={(e) => setMyStatus(e.target.value)} className="input">
              <option value="all">All Statuses</option>
              <option value="draft">Draft</option>
              <option value="submitted">Submitted</option>
              <option value="approved">Approved</option>
              <option value="rejected">Rejected</option>
            </select>
          </div>
          <div>
            <label className="label">Format</label>
            <select value={myFormat} onChange={(e) => setMyFormat(e.target.value)} className="input">
              <option value="csv">CSV</option>
              <option value="excel">Excel</option>
            </select>
          </div>
        </div>

        <div>
          <label className="label">Pay Period Filter</label>
          <select
            value={myPayPeriodStatus}
            onChange={(e) => setMyPayPeriodStatus(e.target.value as any)}
            className="input"
          >
            <option value="all">All Pay Periods</option>
            <option value="open">Open Only</option>
            <option value="closed">Closed Only</option>
          </select>
        </div>

        <label className="flex items-center gap-2 text-sm text-gray-700">
          <input
            type="checkbox"
            checked={myIncludePto}
            onChange={(e) => setMyIncludePto(e.target.checked)}
            className="rounded border-gray-300"
          />
          Include PTO entries
        </label>

        <DownloadButton
          label="Download My Time"
          onClick={downloadMyTime}
          disabled={!myStartDate || !myEndDate}
          loading={isDownloading('my-time')}
        />
      </div>

      {/* ============ SECTION: Manager/Admin Reports ============ */}
      {isManager && (
        <>
          {/* Employee Detail Report */}
          <div className="card p-4 space-y-4">
            <div>
              <h3 className="font-semibold text-gray-900 text-lg">Employee Detail Report</h3>
              <p className="text-sm text-gray-500">
                Day-grouped time entries for selected employees (includes draft timesheets)
              </p>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="label">Start Date</label>
                <input
                  type="date"
                  value={detailStartDate}
                  onChange={(e) => setDetailStartDate(e.target.value)}
                  className="input"
                />
              </div>
              <div>
                <label className="label">End Date</label>
                <input
                  type="date"
                  value={detailEndDate}
                  onChange={(e) => setDetailEndDate(e.target.value)}
                  className="input"
                />
              </div>
            </div>

            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="label">Status Filter</label>
                <select
                  value={detailStatus}
                  onChange={(e) => setDetailStatus(e.target.value)}
                  className="input"
                >
                  <option value="all">All Statuses</option>
                  <option value="draft">Draft</option>
                  <option value="submitted">Submitted</option>
                  <option value="approved">Approved</option>
                  <option value="rejected">Rejected</option>
                </select>
              </div>
              <div>
                <label className="label">Pay Period Filter</label>
                <select
                  value={detailPayPeriodStatus}
                  onChange={(e) => setDetailPayPeriodStatus(e.target.value as any)}
                  className="input"
                >
                  <option value="all">All Pay Periods</option>
                  <option value="open">Open Only</option>
                  <option value="closed">Closed Only</option>
                </select>
              </div>
              <div>
                <label className="label">Format</label>
                <select
                  value={detailFormat}
                  onChange={(e) => setDetailFormat(e.target.value)}
                  className="input"
                >
                  <option value="csv">CSV</option>
                  <option value="excel">Excel</option>
                </select>
              </div>
            </div>

            <label className="flex items-center gap-2 text-sm text-gray-700">
              <input
                type="checkbox"
                checked={detailIncludePto}
                onChange={(e) => setDetailIncludePto(e.target.checked)}
                className="rounded border-gray-300"
              />
              Include PTO entries
            </label>

            {/* Employee selector */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="label mb-0">Select Employees</label>
                <button
                  type="button"
                  onClick={selectAllEmployees}
                  className="text-xs text-primary-600 hover:text-primary-800"
                >
                  {selectedEmployees.length === (employees?.length || 0)
                    ? 'Deselect All'
                    : 'Select All'}
                </button>
              </div>
              <div className="border border-gray-300 rounded-lg max-h-48 overflow-y-auto p-2 space-y-1">
                {employees?.map((emp) => (
                  <label
                    key={emp.id}
                    className="flex items-center gap-2 px-2 py-1.5 rounded hover:bg-gray-50 cursor-pointer text-sm"
                  >
                    <input
                      type="checkbox"
                      checked={selectedEmployees.includes(emp.id)}
                      onChange={() => toggleEmployee(emp.id)}
                      className="rounded border-gray-300"
                    />
                    <span>
                      {emp.last_name}, {emp.first_name}
                    </span>
                  </label>
                ))}
              </div>
              {selectedEmployees.length > 0 && (
                <p className="text-xs text-gray-500 mt-1">
                  {selectedEmployees.length} employee{selectedEmployees.length !== 1 ? 's' : ''}{' '}
                  selected
                </p>
              )}
            </div>

            <DownloadButton
              label={`Download Detail (${selectedEmployees.length} employee${selectedEmployees.length !== 1 ? 's' : ''})`}
              onClick={downloadEmployeeDetail}
              disabled={selectedEmployees.length === 0 || !detailStartDate || !detailEndDate}
              loading={isDownloading('employee-detail')}
            />
          </div>

          {/* Biweekly Payroll Rollup */}
          <div className="card p-4 space-y-4">
            <div>
              <h3 className="font-semibold text-gray-900 text-lg">Biweekly Payroll Rollup</h3>
              <p className="text-sm text-gray-500">
                One row per employee with daily hours for two consecutive pay periods (approved only)
              </p>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="label">Pay Group</label>
                <select
                  value={biweeklyGroup}
                  onChange={(e) => {
                    setBiweeklyGroup(e.target.value)
                    setBiweeklyAnchor('')
                  }}
                  className="input"
                >
                  <option value="A">Group A</option>
                  <option value="B">Group B</option>
                </select>
              </div>
              <div>
                <label className="label">Starting Period</label>
                <select
                  value={biweeklyAnchor}
                  onChange={(e) => setBiweeklyAnchor(e.target.value)}
                  className="input"
                >
                  <option value="">Choose period...</option>
                  {groupPeriods.map((pp) => (
                    <option key={pp.id} value={pp.start_date}>
                      {format(parseISO(pp.start_date), 'MMM d')} -{' '}
                      {format(parseISO(pp.end_date), 'MMM d, yyyy')}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div>
              <label className="label">Format</label>
              <select
                value={biweeklyFormat}
                onChange={(e) => setBiweeklyFormat(e.target.value)}
                className="input"
              >
                <option value="csv">CSV</option>
                <option value="excel">Excel</option>
              </select>
            </div>

            <DownloadButton
              label="Download Biweekly Rollup"
              onClick={downloadBiweekly}
              disabled={!biweeklyAnchor}
              loading={isDownloading('biweekly')}
            />
          </div>

          {/* Pay-Period-Based Reports */}
          <div className="card p-4 space-y-4">
            <div>
              <h3 className="font-semibold text-gray-900 text-lg">Pay Period Reports</h3>
              <p className="text-sm text-gray-500">
                Standard payroll and billing exports by pay period
              </p>
            </div>

            <div>
              <label className="label">Select Pay Period</label>
              <select
                value={selectedPayPeriod}
                onChange={(e) => setSelectedPayPeriod(e.target.value)}
                className="input"
              >
                <option value="">Choose a pay period...</option>
                {payPeriods?.map((pp) => (
                  <option key={pp.id} value={pp.id}>
                    {pp.period_group} - {format(parseISO(pp.start_date), 'MMM d')} to{' '}
                    {format(parseISO(pp.end_date), 'MMM d, yyyy')} ({pp.status})
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="font-medium text-gray-900">Payroll Report</h4>
                  <p className="text-xs text-gray-500">Employee hours summary</p>
                </div>
                <DownloadButton
                  label="CSV"
                  onClick={() => downloadPeriodReport('payroll')}
                  disabled={!selectedPayPeriod}
                  loading={isDownloading('payroll')}
                />
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <h4 className="font-medium text-gray-900">Billing Report</h4>
                  <p className="text-xs text-gray-500">Hours by client for invoicing</p>
                </div>
                <DownloadButton
                  label="CSV"
                  onClick={() => downloadPeriodReport('billing')}
                  disabled={!selectedPayPeriod}
                  loading={isDownloading('billing')}
                />
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <h4 className="font-medium text-gray-900">Engage Export</h4>
                  <p className="text-xs text-gray-500">Formatted for Engage payroll import</p>
                </div>
                <DownloadButton
                  label="Export"
                  onClick={() => downloadPeriodReport('engage')}
                  disabled={!selectedPayPeriod}
                  loading={isDownloading('engage')}
                  variant="success"
                />
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
