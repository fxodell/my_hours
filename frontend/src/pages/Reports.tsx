import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { format, parseISO, subDays } from 'date-fns'
import * as api from '../services/api'
import { useAuth } from '../contexts/AuthContext'
import { useCompany } from '../contexts/CompanyContext'
import CompanySelector from '../components/CompanySelector'
import type {
  PayrollReport,
  BillingReport,
  DetailReport,
  HoursByEmployeeReport,
  HoursBySiteCodeReport,
} from '../types/reports'

// ---------- shared helpers ----------

const DownloadIcon = () => (
  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
  </svg>
)

const PreviewIcon = () => (
  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
  </svg>
)

function ActionButton({ label, onClick, disabled, loading, icon, variant = 'primary' }: {
  label: string; onClick: () => void; disabled: boolean; loading: boolean
  icon: React.ReactNode; variant?: 'primary' | 'success' | 'secondary'
}) {
  const cls = variant === 'success' ? 'btn-success' : variant === 'secondary' ? 'btn-secondary' : 'btn-primary'
  return (
    <button onClick={onClick} disabled={disabled || loading} className={cls}>
      {loading ? (
        <span className="flex items-center gap-2">
          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-current" />
          Loading...
        </span>
      ) : (
        <span className="flex items-center gap-2">{icon}{label}</span>
      )}
    </button>
  )
}

function triggerDownload(blob: Blob, filename: string) {
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = filename
  document.body.appendChild(a); a.click()
  window.URL.revokeObjectURL(url); document.body.removeChild(a)
}

function Th({ children }: { children: React.ReactNode }) {
  return <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase whitespace-nowrap">{children}</th>
}
function Td({ children, className = '', colSpan }: { children: React.ReactNode; className?: string; colSpan?: number }) {
  return <td colSpan={colSpan} className={`px-3 py-2 text-sm text-gray-700 whitespace-nowrap ${className}`}>{children}</td>
}
function Num({ v }: { v: number }) {
  return <span className="tabular-nums">{v.toFixed(1)}</span>
}

function PreviewWrapper({ title, onClose, children }: { title: string; onClose: () => void; children: React.ReactNode }) {
  return (
    <div className="mt-4 border border-gray-200 rounded-lg overflow-hidden">
      <div className="flex items-center justify-between bg-gray-50 px-4 py-2 border-b">
        <h4 className="text-sm font-semibold text-gray-700">{title}</h4>
        <button onClick={onClose} className="text-xs text-gray-500 hover:text-gray-700">Close Preview</button>
      </div>
      <div className="overflow-x-auto max-h-[28rem] overflow-y-auto">{children}</div>
    </div>
  )
}

function EmptyState() {
  return <p className="text-sm text-gray-500 px-4 py-6 text-center">No data found for the selected filters.</p>
}

// ---------- preview sub-tables ----------

function PayrollPreview({ data }: { data: PayrollReport }) {
  if (data.data.length === 0) return <EmptyState />
  const totals = data.data.reduce((acc, r) => ({
    regular: acc.regular + r.regular_hours,
    ot: acc.ot + r.overtime_hours,
    pto: acc.pto + r.total_pto_hours,
    total: acc.total + r.total_hours,
  }), { regular: 0, ot: 0, pto: 0, total: 0 })

  return (
    <>
      <p className="text-xs text-gray-500 px-4 py-2">{data.data.length} employee(s)</p>
      <table className="min-w-full" aria-label="Payroll preview">
        <thead className="bg-gray-50 sticky top-0"><tr>
          <Th>Employee</Th><Th>Period</Th><Th>Regular</Th><Th>OT</Th><Th>PTO</Th><Th>Total</Th>
        </tr></thead>
        <tbody className="divide-y divide-gray-100">
          {data.data.map((r, i) => (
            <tr key={i}>
              <Td>{r.employee_name}</Td>
              <Td>{r.pay_period_start} – {r.pay_period_end}</Td>
              <Td><Num v={r.regular_hours} /></Td>
              <Td><Num v={r.overtime_hours} /></Td>
              <Td><Num v={r.total_pto_hours} /></Td>
              <Td className="font-semibold"><Num v={r.total_hours} /></Td>
            </tr>
          ))}
        </tbody>
        <tfoot className="bg-gray-50 font-semibold"><tr>
          <Td>Total</Td><Td>{'\u00A0'}</Td>
          <Td><Num v={totals.regular} /></Td><Td><Num v={totals.ot} /></Td>
          <Td><Num v={totals.pto} /></Td><Td><Num v={totals.total} /></Td>
        </tr></tfoot>
      </table>
    </>
  )
}

function BillingPreview({ data }: { data: BillingReport }) {
  if (data.data.length === 0) return <EmptyState />
  const clients = Object.entries(data.summary).sort(([a], [b]) => a.localeCompare(b))
  const totalHours = data.data.reduce((s, r) => s + r.hours, 0)
  return (
    <>
      <p className="text-xs text-gray-500 px-4 py-2">{data.data.length} line(s), {clients.length} client(s), {totalHours.toFixed(1)} total hours</p>
      <table className="min-w-full" aria-label="Billing summary">
        <thead className="bg-gray-50 sticky top-0"><tr>
          <Th>Client</Th><Th>Hours</Th>
        </tr></thead>
        <tbody className="divide-y divide-gray-100">
          {clients.map(([name, { hours }]) => (
            <tr key={name}><Td>{name}</Td><Td><Num v={hours} /></Td></tr>
          ))}
        </tbody>
        <tfoot className="bg-gray-50 font-semibold"><tr>
          <Td>Total</Td><Td><Num v={totalHours} /></Td>
        </tr></tfoot>
      </table>
      <details className="px-4 py-2">
        <summary className="text-xs text-gray-500 cursor-pointer">Show all {data.data.length} line items</summary>
        <div className="overflow-x-auto mt-2">
          <table className="min-w-full" aria-label="Billing detail">
            <thead className="bg-gray-50"><tr>
              <Th>Date</Th><Th>Client</Th><Th>Location</Th><Th>Employee</Th><Th>Service</Th><Th>Hours</Th>
            </tr></thead>
            <tbody className="divide-y divide-gray-100">
              {data.data.map((r, i) => (
                <tr key={i}>
                  <Td>{r.date}</Td><Td>{r.client}</Td><Td>{r.location}</Td>
                  <Td>{r.employee}</Td><Td>{r.service_type}</Td><Td><Num v={r.hours} /></Td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </>
  )
}

function getISOWeekKey(dateStr: string): string {
  const d = new Date(dateStr + 'T00:00:00')
  // ISO week: Monday-based. Use local methods consistently to avoid timezone mismatches.
  const tmp = new Date(d.getTime())
  tmp.setDate(tmp.getDate() + 4 - (tmp.getDay() || 7))
  const yearStart = new Date(tmp.getFullYear(), 0, 1)
  const weekNo = Math.ceil(((tmp.getTime() - yearStart.getTime()) / 86400000 + 1) / 7)
  return `${tmp.getFullYear()}-W${String(weekNo).padStart(2, '0')}`
}

type DisplayRow =
  | { kind: 'data'; row: import('../types/reports').DetailRow }
  | { kind: 'daily_total'; date: string; hours: number }
  | { kind: 'weekly_total'; week: string; hours: number }

function buildDisplayRows(data: DetailReport): DisplayRow[] {
  const rows = data.data
  const daily = data.daily_totals ?? {}
  const weekly = data.weekly_totals ?? {}
  const result: DisplayRow[] = []

  let prevEid: string | null = null
  let prevDate: string | null = null
  let prevWeek: string | null = null

  for (const row of rows) {
    const eid = row.employee_id
    const d = row.work_date
    const wk = getISOWeekKey(d)

    // Employee changed — flush previous day/week
    if (prevEid !== null && eid !== prevEid) {
      if (prevDate && daily[prevEid]?.[prevDate] != null) {
        result.push({ kind: 'daily_total', date: prevDate, hours: daily[prevEid][prevDate] })
      }
      if (prevWeek && weekly[prevEid]?.[prevWeek] != null) {
        result.push({ kind: 'weekly_total', week: prevWeek, hours: weekly[prevEid][prevWeek] })
      }
      prevDate = null
      prevWeek = null
    }

    // Date changed within same employee
    if (prevEid === eid && prevDate !== null && d !== prevDate) {
      result.push({ kind: 'daily_total', date: prevDate, hours: daily[eid]?.[prevDate] ?? 0 })
    }

    // Week changed within same employee
    if (prevEid === eid && prevWeek !== null && wk !== prevWeek) {
      result.push({ kind: 'weekly_total', week: prevWeek, hours: weekly[eid]?.[prevWeek] ?? 0 })
    }

    result.push({ kind: 'data', row })
    prevEid = eid
    prevDate = d
    prevWeek = wk
  }

  // Flush final day/week
  if (prevDate && prevEid && daily[prevEid]?.[prevDate] != null) {
    result.push({ kind: 'daily_total', date: prevDate, hours: daily[prevEid][prevDate] })
  }
  if (prevWeek && prevEid && weekly[prevEid]?.[prevWeek] != null) {
    result.push({ kind: 'weekly_total', week: prevWeek, hours: weekly[prevEid][prevWeek] })
  }

  return result
}

function DetailPreview({ data }: { data: DetailReport }) {
  if (data.data.length === 0) return <EmptyState />
  const displayRows = buildDisplayRows(data)
  return (
    <>
      <div className="px-4 py-2 text-xs text-gray-500 flex gap-4 flex-wrap">
        <span>{data.row_count} row(s)</span>
        <span>Work: {data.grand_total.total_work_hours.toFixed(1)}h</span>
        <span>PTO: {data.grand_total.total_pto_hours.toFixed(1)}h</span>
        <span className="font-semibold text-gray-700">Total: {data.grand_total.total_hours.toFixed(1)}h</span>
      </div>
      {data.summary.length > 1 && (
        <div className="px-4 pb-2">
          <details>
            <summary className="text-xs text-gray-500 cursor-pointer">Per-employee summary</summary>
            <div className="mt-1 space-y-0.5">
              {data.summary.map(s => (
                <p key={s.employee_id} className="text-xs text-gray-600">
                  {s.employee_name}: {s.total_work_hours.toFixed(1)}h work + {s.total_pto_hours.toFixed(1)}h PTO = <strong>{s.total_hours.toFixed(1)}h</strong>
                </p>
              ))}
            </div>
          </details>
        </div>
      )}
      <table className="min-w-full" aria-label="Detail preview">
        <thead className="bg-gray-50 sticky top-0"><tr>
          <Th>Date</Th><Th>Employee</Th><Th>Type</Th><Th>Client / PTO</Th><Th>Location</Th><Th>Site Code</Th><Th>Service</Th><Th>Hours</Th><Th>Status</Th>
        </tr></thead>
        <tbody className="divide-y divide-gray-100">
          {displayRows.map((item, i) => {
            if (item.kind === 'daily_total') {
              return (
                <tr key={`dt-${i}`} className="bg-gray-100 font-semibold text-sm">
                  <Td colSpan={7} className="text-right">Daily Total ({item.date})</Td>
                  <Td><Num v={item.hours} /></Td>
                  <Td>{'\u00A0'}</Td>
                </tr>
              )
            }
            if (item.kind === 'weekly_total') {
              return (
                <tr key={`wt-${i}`} className="bg-gray-200 font-bold text-sm">
                  <Td colSpan={7} className="text-right">Weekly Total ({item.week})</Td>
                  <Td><Num v={item.hours} /></Td>
                  <Td>{'\u00A0'}</Td>
                </tr>
              )
            }
            const r = item.row
            return (
              <tr key={i} className={r.entry_kind === 'pto' ? 'bg-blue-50/40' : ''}>
                <Td>{r.work_date}</Td>
                <Td>{r.employee_name}</Td>
                <Td>{r.entry_kind === 'pto' ? 'PTO' : 'Work'}</Td>
                <Td>{r.entry_kind === 'pto' ? r.pto_type : r.client}</Td>
                <Td>{r.location}</Td>
                <Td>{r.entry_kind === 'work' ? (r.site_code ? `${r.site_code}${r.site_code_description ? ' – ' + r.site_code_description : ''}` : r.site_code_description || '') : ''}</Td>
                <Td>{r.service_type}</Td>
                <Td><Num v={r.hours} /></Td>
                <Td>{r.timesheet_status}</Td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </>
  )
}

function HoursByEmployeePreview({ data }: { data: HoursByEmployeeReport }) {
  if (data.data.length === 0) return <EmptyState />
  const total = data.data.reduce((s, r) => s + r.total_hours, 0)
  return (
    <>
      <p className="text-xs text-gray-500 px-4 py-2">{data.data.length} employee(s), {total.toFixed(1)} total hours</p>
      <table className="min-w-full" aria-label="Hours by employee preview">
        <thead className="bg-gray-50 sticky top-0"><tr>
          <Th>Employee</Th><Th>Email</Th><Th>Hours</Th>
        </tr></thead>
        <tbody className="divide-y divide-gray-100">
          {data.data.map((r, i) => (
            <tr key={i}><Td>{r.employee_name}</Td><Td>{r.email}</Td><Td><Num v={r.total_hours} /></Td></tr>
          ))}
        </tbody>
        <tfoot className="bg-gray-50 font-semibold"><tr>
          <Td>Total</Td><Td>{'\u00A0'}</Td><Td><Num v={total} /></Td>
        </tr></tfoot>
      </table>
    </>
  )
}

function HoursBySiteCodePreview({ data }: { data: HoursBySiteCodeReport }) {
  if (data.data.length === 0) return <EmptyState />
  const total = data.data.reduce((s, r) => s + r.total_hours, 0)
  return (
    <>
      <p className="text-xs text-gray-500 px-4 py-2">{data.data.length} group(s), {total.toFixed(1)} total hours</p>
      <table className="min-w-full" aria-label="Hours by site code preview">
        <thead className="bg-gray-50 sticky top-0"><tr>
          <Th>Client</Th><Th>Service Type</Th><Th>Site Code</Th><Th>Hours</Th>
        </tr></thead>
        <tbody className="divide-y divide-gray-100">
          {data.data.map((r, i) => (
            <tr key={i}><Td>{r.client}</Td><Td>{r.service_type}</Td><Td>{r.site_code}</Td><Td><Num v={r.total_hours} /></Td></tr>
          ))}
        </tbody>
        <tfoot className="bg-gray-50 font-semibold"><tr>
          <Td>Total</Td><Td>{'\u00A0'}</Td><Td>{'\u00A0'}</Td><Td><Num v={total} /></Td>
        </tr></tfoot>
      </table>
    </>
  )
}

// ---------- main component ----------

export default function Reports() {
  const { user } = useAuth()
  const { companyParam } = useCompany()
  const isManager = user?.is_manager || user?.is_admin

  const [activeDownloads, setActiveDownloads] = useState<Set<string>>(new Set())
  const [error, setError] = useState('')

  // My Time state
  const [myStartDate, setMyStartDate] = useState(format(subDays(new Date(), 30), 'yyyy-MM-dd'))
  const [myEndDate, setMyEndDate] = useState(format(new Date(), 'yyyy-MM-dd'))
  const [myStatus, setMyStatus] = useState('all')
  const [myPayPeriodStatus, setMyPayPeriodStatus] = useState<'all' | 'open' | 'closed'>('all')
  const [myFormat, setMyFormat] = useState('csv')
  const [myIncludePto, setMyIncludePto] = useState(true)
  const [myPreviewEnabled, setMyPreviewEnabled] = useState(false)

  // Employee detail state
  const [detailStartDate, setDetailStartDate] = useState(format(subDays(new Date(), 30), 'yyyy-MM-dd'))
  const [detailEndDate, setDetailEndDate] = useState(format(new Date(), 'yyyy-MM-dd'))
  const [selectedEmployees, setSelectedEmployees] = useState<string[]>([])
  const [detailStatus, setDetailStatus] = useState('all')
  const [detailPayPeriodStatus, setDetailPayPeriodStatus] = useState<'all' | 'open' | 'closed'>('all')
  const [detailFormat, setDetailFormat] = useState('csv')
  const [detailIncludePto, setDetailIncludePto] = useState(true)
  const [detailPreviewEnabled, setDetailPreviewEnabled] = useState(false)

  // Pay period reports
  const [selectedPayPeriod, setSelectedPayPeriod] = useState<string>('')
  const [payrollPreviewEnabled, setPayrollPreviewEnabled] = useState(false)
  const [billingPreviewEnabled, setBillingPreviewEnabled] = useState(false)

  // Hours by Employee / Site Code state
  const [hbeStartDate, setHbeStartDate] = useState(format(subDays(new Date(), 30), 'yyyy-MM-dd'))
  const [hbeEndDate, setHbeEndDate] = useState(format(new Date(), 'yyyy-MM-dd'))
  const [hbePreviewEnabled, setHbePreviewEnabled] = useState(false)
  const [hbjcStartDate, setHbjcStartDate] = useState(format(subDays(new Date(), 30), 'yyyy-MM-dd'))
  const [hbjcEndDate, setHbjcEndDate] = useState(format(new Date(), 'yyyy-MM-dd'))
  const [hbjcClientFilter, setHbjcClientFilter] = useState<string>('')
  const [hbjcPreviewEnabled, setHbjcPreviewEnabled] = useState(false)

  // Data queries
  const { data: payPeriods, isLoading } = useQuery({
    queryKey: ['payPeriods', companyParam],
    queryFn: () => api.getPayPeriods(20, companyParam),
  })
  const { data: employees } = useQuery({
    queryKey: ['employees', companyParam],
    queryFn: () => api.getEmployees(companyParam),
    enabled: isManager ?? false,
  })
  const { data: clients } = useQuery({
    queryKey: ['clients', companyParam],
    queryFn: () => api.getClients(companyParam),
    enabled: isManager ?? false,
  })
  // === Preview queries (on-demand) ===
  const myTimePreview = useQuery({
    queryKey: ['preview', 'my-time', myStartDate, myEndDate, myStatus, myPayPeriodStatus, myIncludePto],
    queryFn: () => api.previewMyTimeDetail({
      startDate: myStartDate, endDate: myEndDate,
      timesheetStatus: myStatus !== 'all' ? myStatus : undefined,
      payPeriodStatus: myPayPeriodStatus, includePto: myIncludePto,
    }),
    enabled: myPreviewEnabled && !!myStartDate && !!myEndDate,
  })

  const detailPreview = useQuery({
    queryKey: ['preview', 'detail', selectedEmployees, detailStartDate, detailEndDate, detailStatus, detailPayPeriodStatus, detailIncludePto, companyParam],
    queryFn: () => api.previewEmployeeDetail({
      employeeIds: selectedEmployees, startDate: detailStartDate, endDate: detailEndDate,
      timesheetStatus: detailStatus !== 'all' ? detailStatus : undefined,
      payPeriodStatus: detailPayPeriodStatus, includePto: detailIncludePto, companyId: companyParam,
    }),
    enabled: detailPreviewEnabled && selectedEmployees.length > 0 && !!detailStartDate && !!detailEndDate,
  })

  const payrollPreview = useQuery({
    queryKey: ['preview', 'payroll', selectedPayPeriod, companyParam],
    queryFn: () => api.previewPayroll(selectedPayPeriod, companyParam),
    enabled: payrollPreviewEnabled && !!selectedPayPeriod,
  })

  const pp = payPeriods?.find(p => p.id === selectedPayPeriod)
  const billingPreview = useQuery({
    queryKey: ['preview', 'billing', pp?.start_date, pp?.end_date, companyParam],
    queryFn: () => api.previewBilling(pp?.start_date, pp?.end_date, companyParam),
    enabled: billingPreviewEnabled && !!selectedPayPeriod && !!pp,
  })

  const hbePreview = useQuery({
    queryKey: ['preview', 'hbe', hbeStartDate, hbeEndDate, companyParam],
    queryFn: () => api.previewHoursByEmployee(hbeStartDate, hbeEndDate, companyParam),
    enabled: hbePreviewEnabled && !!hbeStartDate && !!hbeEndDate,
  })

  const hbjcPreview = useQuery({
    queryKey: ['preview', 'hbjc', hbjcStartDate, hbjcEndDate, hbjcClientFilter, companyParam],
    queryFn: () => api.previewHoursBySiteCode({ startDate: hbjcStartDate, endDate: hbjcEndDate, clientId: hbjcClientFilter || undefined, companyId: companyParam }),
    enabled: hbjcPreviewEnabled && !!hbjcStartDate && !!hbjcEndDate,
  })

  // download helpers
  const startDownload = (k: string) => { setActiveDownloads(p => new Set(p).add(k)); setError('') }
  const endDownload = (k: string) => { setActiveDownloads(p => { const n = new Set(p); n.delete(k); return n }) }
  const isDownloading = (k: string) => activeDownloads.has(k)

  const downloadPeriodReport = async (type: 'payroll' | 'billing' | 'engage') => {
    if (!selectedPayPeriod) return
    startDownload(type)
    try {
      let blob: Blob
      if (type === 'payroll') {
        blob = await api.getPayrollReport(selectedPayPeriod, companyParam)
      } else if (type === 'billing') {
        blob = await api.getBillingReport(pp?.start_date, pp?.end_date, companyParam)
      } else {
        blob = await api.getEngageExport(selectedPayPeriod, companyParam)
      }
      triggerDownload(blob, `${type}-report-${format(new Date(), 'yyyy-MM-dd')}.csv`)
    } catch (err: any) { setError(err.message || 'Download failed') }
    finally { endDownload(type) }
  }

  const downloadMyTime = async () => {
    if (myStartDate > myEndDate) { setError('Start date must be before end date'); return }
    startDownload('my-time')
    try {
      const blob = await api.getMyTimeDetailReport({
        startDate: myStartDate, endDate: myEndDate,
        timesheetStatus: myStatus !== 'all' ? myStatus : undefined,
        payPeriodStatus: myPayPeriodStatus, includePto: myIncludePto, format: myFormat,
      })
      triggerDownload(blob, `my-time-${myStartDate}-to-${myEndDate}.${myFormat === 'excel' ? 'xlsx' : myFormat}`)
    } catch (err: any) { setError(err.message || 'Download failed') }
    finally { endDownload('my-time') }
  }

  const downloadEmployeeDetail = async () => {
    if (selectedEmployees.length === 0) return
    if (detailStartDate > detailEndDate) { setError('Start date must be before end date'); return }
    startDownload('employee-detail')
    try {
      const blob = await api.getEmployeeDetailReport({
        employeeIds: selectedEmployees, startDate: detailStartDate, endDate: detailEndDate,
        timesheetStatus: detailStatus !== 'all' ? detailStatus : undefined,
        payPeriodStatus: detailPayPeriodStatus, includePto: detailIncludePto,
        format: detailFormat, companyId: companyParam,
      })
      triggerDownload(blob, `employee-detail-${detailStartDate}-to-${detailEndDate}.${detailFormat === 'excel' ? 'xlsx' : detailFormat}`)
    } catch (err: any) { setError(err.message || 'Download failed') }
    finally { endDownload('employee-detail') }
  }

  const downloadHoursByEmployee = async () => {
    startDownload('hbe')
    try {
      const blob = await api.getHoursByEmployeeReport(hbeStartDate, hbeEndDate, companyParam)
      triggerDownload(blob, `hours-by-employee-${hbeStartDate}-to-${hbeEndDate}.csv`)
    } catch (err: any) { setError(err.message || 'Download failed') }
    finally { endDownload('hbe') }
  }

  const downloadHoursBySiteCode = async () => {
    startDownload('hbjc')
    try {
      const blob = await api.getHoursBySiteCodeReport({
        startDate: hbjcStartDate, endDate: hbjcEndDate,
        clientId: hbjcClientFilter || undefined, companyId: companyParam,
      })
      triggerDownload(blob, `hours-by-site-code-${hbjcStartDate}-to-${hbjcEndDate}.csv`)
    } catch (err: any) { setError(err.message || 'Download failed') }
    finally { endDownload('hbjc') }
  }

  const toggleEmployee = (id: string) =>
    setSelectedEmployees(prev => prev.includes(id) ? prev.filter(e => e !== id) : [...prev, id])
  const selectAllEmployees = () => {
    if (!employees) return
    setSelectedEmployees(prev => prev.length === employees.length ? [] : employees.map(e => e.id))
  }

  if (isLoading) {
    return <div className="flex justify-center py-12"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" /></div>
  }

  return (
    <div className="space-y-6 pb-4">
      <CompanySelector />
      <h2 className="text-xl font-bold text-gray-900">Reports</h2>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
          {error}
        </div>
      )}

      {/* ============ My Time ============ */}
      <div className="card p-4 space-y-4">
        <div>
          <h3 className="font-semibold text-gray-900 text-lg">My Time</h3>
          <p className="text-sm text-gray-500">Preview or export your own time entries</p>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div><label className="label">Start Date</label><input type="date" value={myStartDate} onChange={e => setMyStartDate(e.target.value)} className="input" /></div>
          <div><label className="label">End Date</label><input type="date" value={myEndDate} onChange={e => setMyEndDate(e.target.value)} className="input" /></div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div><label className="label">Status Filter</label>
            <select value={myStatus} onChange={e => setMyStatus(e.target.value)} className="input">
              <option value="all">All Statuses</option><option value="draft">Draft</option>
              <option value="submitted">Submitted</option><option value="approved">Approved</option><option value="rejected">Rejected</option>
            </select>
          </div>
          <div><label className="label">Format</label>
            <select value={myFormat} onChange={e => setMyFormat(e.target.value)} className="input">
              <option value="csv">CSV</option><option value="excel">Excel</option>
            </select>
          </div>
        </div>
        <div><label className="label">Pay Period Filter</label>
          <select value={myPayPeriodStatus} onChange={e => setMyPayPeriodStatus(e.target.value as any)} className="input">
            <option value="all">All Pay Periods</option><option value="open">Open Only</option><option value="closed">Closed Only</option>
          </select>
        </div>
        <label className="flex items-center gap-2 text-sm text-gray-700">
          <input type="checkbox" checked={myIncludePto} onChange={e => setMyIncludePto(e.target.checked)} className="rounded border-gray-300" />
          Include PTO entries
        </label>
        <div className="flex gap-2 flex-wrap">
          <ActionButton label="Preview" onClick={() => setMyPreviewEnabled(true)} disabled={!myStartDate || !myEndDate} loading={myTimePreview.isFetching} icon={<PreviewIcon />} variant="secondary" />
          <ActionButton label={`Download ${myFormat.toUpperCase()}`} onClick={downloadMyTime} disabled={!myStartDate || !myEndDate} loading={isDownloading('my-time')} icon={<DownloadIcon />} />
        </div>
        {myPreviewEnabled && myTimePreview.error && <p className="text-sm text-red-600">{myTimePreview.error instanceof Error ? myTimePreview.error.message : 'Preview failed'}</p>}
        {myPreviewEnabled && myTimePreview.data && (
          <PreviewWrapper title="My Time Preview" onClose={() => setMyPreviewEnabled(false)}>
            <DetailPreview data={myTimePreview.data} />
          </PreviewWrapper>
        )}
      </div>

      {/* ============ Manager/Admin sections ============ */}
      {isManager && (
        <>
          {/* Employee Detail */}
          <div className="card p-4 space-y-4">
            <div>
              <h3 className="font-semibold text-gray-900 text-lg">Employee Detail Report</h3>
              <p className="text-sm text-gray-500">Day-grouped time entries for selected employees (includes draft timesheets)</p>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div><label className="label">Start Date</label><input type="date" value={detailStartDate} onChange={e => setDetailStartDate(e.target.value)} className="input" /></div>
              <div><label className="label">End Date</label><input type="date" value={detailEndDate} onChange={e => setDetailEndDate(e.target.value)} className="input" /></div>
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div><label className="label">Status Filter</label>
                <select value={detailStatus} onChange={e => setDetailStatus(e.target.value)} className="input">
                  <option value="all">All Statuses</option><option value="draft">Draft</option>
                  <option value="submitted">Submitted</option><option value="approved">Approved</option><option value="rejected">Rejected</option>
                </select>
              </div>
              <div><label className="label">Pay Period Filter</label>
                <select value={detailPayPeriodStatus} onChange={e => setDetailPayPeriodStatus(e.target.value as any)} className="input">
                  <option value="all">All</option><option value="open">Open</option><option value="closed">Closed</option>
                </select>
              </div>
              <div><label className="label">Format</label>
                <select value={detailFormat} onChange={e => setDetailFormat(e.target.value)} className="input">
                  <option value="csv">CSV</option><option value="excel">Excel</option>
                </select>
              </div>
            </div>
            <label className="flex items-center gap-2 text-sm text-gray-700">
              <input type="checkbox" checked={detailIncludePto} onChange={e => setDetailIncludePto(e.target.checked)} className="rounded border-gray-300" /> Include PTO
            </label>
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="label mb-0">Select Employees</label>
                <button type="button" onClick={selectAllEmployees} className="text-xs text-primary-600 hover:text-primary-800">
                  {selectedEmployees.length === (employees?.length || 0) ? 'Deselect All' : 'Select All'}
                </button>
              </div>
              <div className="border border-gray-300 rounded-lg max-h-48 overflow-y-auto p-2 space-y-1">
                {employees?.map(emp => (
                  <label key={emp.id} className="flex items-center gap-2 px-2 py-1.5 rounded hover:bg-gray-50 cursor-pointer text-sm">
                    <input type="checkbox" checked={selectedEmployees.includes(emp.id)} onChange={() => toggleEmployee(emp.id)} className="rounded border-gray-300" />
                    <span>{emp.last_name}, {emp.first_name}</span>
                  </label>
                ))}
              </div>
              {selectedEmployees.length > 0 && <p className="text-xs text-gray-500 mt-1">{selectedEmployees.length} employee{selectedEmployees.length !== 1 ? 's' : ''} selected</p>}
            </div>
            <div className="flex gap-2 flex-wrap">
              <ActionButton label="Preview" onClick={() => setDetailPreviewEnabled(true)} disabled={selectedEmployees.length === 0 || !detailStartDate || !detailEndDate} loading={detailPreview.isFetching} icon={<PreviewIcon />} variant="secondary" />
              <ActionButton label={`Download ${detailFormat.toUpperCase()} (${selectedEmployees.length})`} onClick={downloadEmployeeDetail} disabled={selectedEmployees.length === 0 || !detailStartDate || !detailEndDate} loading={isDownloading('employee-detail')} icon={<DownloadIcon />} />
            </div>
            {detailPreviewEnabled && detailPreview.error && <p className="text-sm text-red-600">{detailPreview.error instanceof Error ? detailPreview.error.message : 'Preview failed'}</p>}
            {detailPreviewEnabled && detailPreview.data && (
              <PreviewWrapper title="Employee Detail Preview" onClose={() => setDetailPreviewEnabled(false)}>
                <DetailPreview data={detailPreview.data} />
              </PreviewWrapper>
            )}
          </div>

          {/* Pay Period Reports */}
          <div className="card p-4 space-y-4">
            <div>
              <h3 className="font-semibold text-gray-900 text-lg">Pay Period Reports</h3>
              <p className="text-sm text-gray-500">Standard payroll and billing exports by pay period</p>
            </div>
            <div><label className="label">Select Pay Period</label>
              <select value={selectedPayPeriod} onChange={e => { setSelectedPayPeriod(e.target.value); setPayrollPreviewEnabled(false); setBillingPreviewEnabled(false) }} className="input">
                <option value="">Choose a pay period...</option>
                {payPeriods?.map(pp => (
                  <option key={pp.id} value={pp.id}>
                    {pp.period_group} - {format(parseISO(pp.start_date), 'MMM d')} to {format(parseISO(pp.end_date), 'MMM d, yyyy')} ({pp.status})
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-3">
              {/* Payroll */}
              <div>
                <div className="flex items-center justify-between">
                  <div><h4 className="font-medium text-gray-900">Payroll Report</h4><p className="text-xs text-gray-500">Employee hours summary</p></div>
                  <div className="flex gap-2">
                    <ActionButton label="Preview" onClick={() => setPayrollPreviewEnabled(true)} disabled={!selectedPayPeriod} loading={payrollPreview.isFetching} icon={<PreviewIcon />} variant="secondary" />
                    <ActionButton label="CSV" onClick={() => downloadPeriodReport('payroll')} disabled={!selectedPayPeriod} loading={isDownloading('payroll')} icon={<DownloadIcon />} />
                  </div>
                </div>
                {payrollPreviewEnabled && payrollPreview.error && <p className="text-sm text-red-600 mt-1">{payrollPreview.error instanceof Error ? payrollPreview.error.message : 'Preview failed'}</p>}
                {payrollPreviewEnabled && payrollPreview.data && (
                  <PreviewWrapper title="Payroll Preview" onClose={() => setPayrollPreviewEnabled(false)}>
                    <PayrollPreview data={payrollPreview.data} />
                  </PreviewWrapper>
                )}
              </div>

              {/* Billing */}
              <div>
                <div className="flex items-center justify-between">
                  <div><h4 className="font-medium text-gray-900">Billing Report</h4><p className="text-xs text-gray-500">Hours by client for invoicing</p></div>
                  <div className="flex gap-2">
                    <ActionButton label="Preview" onClick={() => setBillingPreviewEnabled(true)} disabled={!selectedPayPeriod} loading={billingPreview.isFetching} icon={<PreviewIcon />} variant="secondary" />
                    <ActionButton label="CSV" onClick={() => downloadPeriodReport('billing')} disabled={!selectedPayPeriod} loading={isDownloading('billing')} icon={<DownloadIcon />} />
                  </div>
                </div>
                {billingPreviewEnabled && billingPreview.error && <p className="text-sm text-red-600 mt-1">{billingPreview.error instanceof Error ? billingPreview.error.message : 'Preview failed'}</p>}
                {billingPreviewEnabled && billingPreview.data && (
                  <PreviewWrapper title="Billing Preview" onClose={() => setBillingPreviewEnabled(false)}>
                    <BillingPreview data={billingPreview.data} />
                  </PreviewWrapper>
                )}
              </div>

              {/* Engage */}
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="font-medium text-gray-900">Engage Export</h4>
                  <p className="text-xs text-gray-500">Formatted for Engage payroll import (download only)</p>
                </div>
                <ActionButton label="Export" onClick={() => downloadPeriodReport('engage')} disabled={!selectedPayPeriod} loading={isDownloading('engage')} icon={<DownloadIcon />} variant="success" />
              </div>
            </div>
          </div>

          {/* Hours by Employee */}
          <div className="card p-4 space-y-4">
            <div>
              <h3 className="font-semibold text-gray-900 text-lg">Hours by Employee</h3>
              <p className="text-sm text-gray-500">Total approved hours per employee for a date range</p>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div><label className="label">Start Date</label><input type="date" value={hbeStartDate} onChange={e => setHbeStartDate(e.target.value)} className="input" /></div>
              <div><label className="label">End Date</label><input type="date" value={hbeEndDate} onChange={e => setHbeEndDate(e.target.value)} className="input" /></div>
            </div>
            <div className="flex gap-2 flex-wrap">
              <ActionButton label="Preview" onClick={() => setHbePreviewEnabled(true)} disabled={!hbeStartDate || !hbeEndDate} loading={hbePreview.isFetching} icon={<PreviewIcon />} variant="secondary" />
              <ActionButton label="Download CSV" onClick={downloadHoursByEmployee} disabled={!hbeStartDate || !hbeEndDate} loading={isDownloading('hbe')} icon={<DownloadIcon />} />
            </div>
            {hbePreviewEnabled && hbePreview.error && <p className="text-sm text-red-600">{hbePreview.error instanceof Error ? hbePreview.error.message : 'Preview failed'}</p>}
            {hbePreviewEnabled && hbePreview.data && (
              <PreviewWrapper title="Hours by Employee Preview" onClose={() => setHbePreviewEnabled(false)}>
                <HoursByEmployeePreview data={hbePreview.data} />
              </PreviewWrapper>
            )}
          </div>

          {/* Hours by Site Code */}
          <div className="card p-4 space-y-4">
            <div>
              <h3 className="font-semibold text-gray-900 text-lg">Hours by Site Code</h3>
              <p className="text-sm text-gray-500">Approved hours grouped by client, service type, and site code</p>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div><label className="label">Start Date</label><input type="date" value={hbjcStartDate} onChange={e => setHbjcStartDate(e.target.value)} className="input" /></div>
              <div><label className="label">End Date</label><input type="date" value={hbjcEndDate} onChange={e => setHbjcEndDate(e.target.value)} className="input" /></div>
            </div>
            <div>
              <label className="label">Client Filter</label>
              <select value={hbjcClientFilter} onChange={e => { setHbjcClientFilter(e.target.value); setHbjcPreviewEnabled(false) }} className="input">
                <option value="">All Clients</option>
                {clients?.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>
            <div className="flex gap-2 flex-wrap">
              <ActionButton label="Preview" onClick={() => setHbjcPreviewEnabled(true)} disabled={!hbjcStartDate || !hbjcEndDate} loading={hbjcPreview.isFetching} icon={<PreviewIcon />} variant="secondary" />
              <ActionButton label="Download CSV" onClick={downloadHoursBySiteCode} disabled={!hbjcStartDate || !hbjcEndDate} loading={isDownloading('hbjc')} icon={<DownloadIcon />} />
            </div>
            {hbjcPreviewEnabled && hbjcPreview.error && <p className="text-sm text-red-600">{hbjcPreview.error instanceof Error ? hbjcPreview.error.message : 'Preview failed'}</p>}
            {hbjcPreviewEnabled && hbjcPreview.data && (
              <PreviewWrapper title="Hours by Site Code Preview" onClose={() => setHbjcPreviewEnabled(false)}>
                <HoursBySiteCodePreview data={hbjcPreview.data} />
              </PreviewWrapper>
            )}
          </div>
        </>
      )}
    </div>
  )
}
