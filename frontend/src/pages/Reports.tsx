import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { format, parseISO } from 'date-fns'
import * as api from '../services/api'
import { useAuth } from '../contexts/AuthContext'

export default function Reports() {
  const { user } = useAuth()
  const [selectedPayPeriod, setSelectedPayPeriod] = useState<string>('')
  const [downloading, setDownloading] = useState<string | null>(null)

  const { data: payPeriods, isLoading } = useQuery({
    queryKey: ['payPeriods'],
    queryFn: () => api.getPayPeriods(20),
  })

  const downloadReport = async (type: 'payroll' | 'billing' | 'engage') => {
    if (!selectedPayPeriod) return

    setDownloading(type)
    try {
      let blob: Blob
      if (type === 'payroll') {
        blob = await api.getPayrollReport(selectedPayPeriod)
      } else if (type === 'billing') {
        blob = await api.getBillingReport(selectedPayPeriod)
      } else {
        blob = await api.getEngageExport(selectedPayPeriod)
      }

      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${type}-report-${format(new Date(), 'yyyy-MM-dd')}.csv`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (err) {
      console.error('Download failed:', err)
      alert('Failed to download report. Please try again.')
    } finally {
      setDownloading(null)
    }
  }

  if (!user?.is_admin && !user?.is_manager) {
    return (
      <div className="text-center py-12 text-gray-500">
        <p>You do not have permission to view reports.</p>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-gray-900">Reports</h2>

      {/* Pay Period Selector */}
      <div className="card p-4">
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

      {/* Report Options */}
      <div className="space-y-3">
        <div className="card p-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-semibold text-gray-900">Payroll Report</h3>
              <p className="text-sm text-gray-500">
                Employee hours summary for Engage payroll import
              </p>
            </div>
            <button
              onClick={() => downloadReport('payroll')}
              disabled={!selectedPayPeriod || downloading === 'payroll'}
              className="btn-primary"
            >
              {downloading === 'payroll' ? (
                <span className="flex items-center gap-2">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  Downloading...
                </span>
              ) : (
                <span className="flex items-center gap-2">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg>
                  Download CSV
                </span>
              )}
            </button>
          </div>
        </div>

        <div className="card p-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-semibold text-gray-900">Billing Report</h3>
              <p className="text-sm text-gray-500">
                Hours by client for invoicing
              </p>
            </div>
            <button
              onClick={() => downloadReport('billing')}
              disabled={!selectedPayPeriod || downloading === 'billing'}
              className="btn-primary"
            >
              {downloading === 'billing' ? (
                <span className="flex items-center gap-2">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  Downloading...
                </span>
              ) : (
                <span className="flex items-center gap-2">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg>
                  Download CSV
                </span>
              )}
            </button>
          </div>
        </div>

        <div className="card p-4 border-2 border-green-200 bg-green-50">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-semibold text-gray-900">Engage Payroll Export</h3>
              <p className="text-sm text-gray-500">
                Formatted specifically for Engage payroll import
              </p>
            </div>
            <button
              onClick={() => downloadReport('engage')}
              disabled={!selectedPayPeriod || downloading === 'engage'}
              className="btn-success"
            >
              {downloading === 'engage' ? (
                <span className="flex items-center gap-2">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  Downloading...
                </span>
              ) : (
                <span className="flex items-center gap-2">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg>
                  Export for Engage
                </span>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Instructions */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h4 className="font-medium text-blue-900 mb-2">Report Information</h4>
        <ul className="text-sm text-blue-800 space-y-1">
          <li>1. Select a pay period from the dropdown above</li>
          <li>2. Download the desired report type</li>
          <li>3. Payroll reports can be imported directly into Engage</li>
          <li>4. Billing reports summarize hours by client for invoicing</li>
        </ul>
      </div>
    </div>
  )
}
