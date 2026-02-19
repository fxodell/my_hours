import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { format, parseISO } from 'date-fns'
import * as api from '../services/api'
import { useAuth } from '../contexts/AuthContext'
import type { PayPeriod } from '../types'

interface PayPeriodFormData {
  period_group: string
  start_date: string
  end_date: string
  payroll_run_date: string
}

interface GenerateFormData {
  start_date: string
  weeks: number
}

export default function PayPeriods() {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [showGenerate, setShowGenerate] = useState(false)
  const [editingPeriod, setEditingPeriod] = useState<PayPeriod | null>(null)
  const [confirmClose, setConfirmClose] = useState<string | null>(null)
  const [filterGroup, setFilterGroup] = useState<string>('')
  const [filterStatus, setFilterStatus] = useState<string>('')
  const [formData, setFormData] = useState<PayPeriodFormData>({
    period_group: 'A',
    start_date: '',
    end_date: '',
    payroll_run_date: '',
  })
  const [generateData, setGenerateData] = useState<GenerateFormData>({
    start_date: '',
    weeks: 8,
  })
  const [error, setError] = useState('')

  const { data: payPeriods, isLoading } = useQuery({
    queryKey: ['payPeriods', 'admin', filterGroup, filterStatus],
    queryFn: () =>
      api.getAllPayPeriods({
        period_group: filterGroup || undefined,
        status_filter: filterStatus || undefined,
        limit: 100,
      }),
  })

  const createMutation = useMutation({
    mutationFn: (data: PayPeriodFormData) =>
      api.createPayPeriod({
        period_group: data.period_group,
        start_date: data.start_date,
        end_date: data.end_date,
        payroll_run_date: data.payroll_run_date || undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['payPeriods'] })
      resetForm()
    },
    onError: (err) => {
      setError(err instanceof Error ? err.message : 'Failed to create pay period')
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<PayPeriodFormData> }) =>
      api.updatePayPeriod(id, {
        ...data,
        payroll_run_date: data.payroll_run_date || null,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['payPeriods'] })
      resetForm()
    },
    onError: (err) => {
      setError(err instanceof Error ? err.message : 'Failed to update pay period')
    },
  })

  const generateMutation = useMutation({
    mutationFn: (data: GenerateFormData) => api.generatePayPeriods(data),
    onSuccess: (created) => {
      queryClient.invalidateQueries({ queryKey: ['payPeriods'] })
      setShowGenerate(false)
      setGenerateData({ start_date: '', weeks: 8 })
      setError('')
      alert(`Generated ${created.length} pay periods.`)
    },
    onError: (err) => {
      setError(err instanceof Error ? err.message : 'Failed to generate pay periods')
    },
  })

  const closeMutation = useMutation({
    mutationFn: (id: string) => api.closePayPeriod(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['payPeriods'] })
      setConfirmClose(null)
    },
    onError: (err) => {
      setError(err instanceof Error ? err.message : 'Failed to close pay period')
      setConfirmClose(null)
    },
  })

  const resetForm = () => {
    setShowForm(false)
    setEditingPeriod(null)
    setFormData({ period_group: 'A', start_date: '', end_date: '', payroll_run_date: '' })
    setError('')
  }

  const handleEdit = (pp: PayPeriod) => {
    setEditingPeriod(pp)
    setFormData({
      period_group: pp.period_group,
      start_date: pp.start_date,
      end_date: pp.end_date,
      payroll_run_date: pp.payroll_run_date || '',
    })
    setShowForm(true)
    setShowGenerate(false)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (editingPeriod) {
      updateMutation.mutate({
        id: editingPeriod.id,
        data: {
          start_date: formData.start_date,
          end_date: formData.end_date,
          payroll_run_date: formData.payroll_run_date,
        },
      })
    } else {
      createMutation.mutate(formData)
    }
  }

  const handleGenerate = (e: React.FormEvent) => {
    e.preventDefault()
    generateMutation.mutate(generateData)
  }

  const statusColors: Record<string, string> = {
    open: 'bg-green-100 text-green-800',
    closed: 'bg-gray-100 text-gray-800',
    processed: 'bg-blue-100 text-blue-800',
  }

  if (!user?.is_admin) {
    return (
      <div className="text-center py-12 text-gray-500">
        <p>You do not have permission to manage pay periods.</p>
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
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-gray-900">Pay Periods</h2>
        {!showForm && !showGenerate && (
          <div className="flex gap-2">
            <button
              onClick={() => { setShowGenerate(true); setShowForm(false) }}
              className="btn-secondary"
            >
              Generate
            </button>
            <button
              onClick={() => { setShowForm(true); setShowGenerate(false) }}
              className="btn-primary"
            >
              Add Period
            </button>
          </div>
        )}
      </div>

      {/* Filters */}
      <div className="flex gap-3">
        <select
          value={filterGroup}
          onChange={(e) => setFilterGroup(e.target.value)}
          className="input w-auto"
        >
          <option value="">All Groups</option>
          <option value="A">Group A</option>
          <option value="B">Group B</option>
        </select>
        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value)}
          className="input w-auto"
        >
          <option value="">All Status</option>
          <option value="open">Open</option>
          <option value="closed">Closed</option>
        </select>
      </div>

      {/* Generate Form */}
      {showGenerate && (
        <div className="card p-4">
          <h3 className="font-semibold text-gray-900 mb-4">Generate Pay Periods</h3>
          <p className="text-sm text-gray-500 mb-4">
            Creates bi-weekly periods for both Group A and Group B, staggered by 1 week.
          </p>

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm mb-4">
              {error}
            </div>
          )}

          <form onSubmit={handleGenerate} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="label">Start Date (Group A)</label>
                <input
                  type="date"
                  value={generateData.start_date}
                  onChange={(e) => setGenerateData({ ...generateData, start_date: e.target.value })}
                  className="input"
                  required
                />
              </div>
              <div>
                <label className="label">Weeks</label>
                <input
                  type="number"
                  value={generateData.weeks}
                  onChange={(e) => setGenerateData({ ...generateData, weeks: parseInt(e.target.value) || 8 })}
                  className="input"
                  min={2}
                  step={2}
                  required
                />
              </div>
            </div>

            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => { setShowGenerate(false); setError('') }}
                className="btn-secondary flex-1"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={generateMutation.isPending}
                className="btn-primary flex-1"
              >
                {generateMutation.isPending ? 'Generating...' : 'Generate Periods'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Create/Edit Form */}
      {showForm && (
        <div className="card p-4">
          <h3 className="font-semibold text-gray-900 mb-4">
            {editingPeriod ? 'Edit Pay Period' : 'Add Single Pay Period'}
          </h3>

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm mb-4">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {!editingPeriod && (
              <div>
                <label className="label">Group</label>
                <select
                  value={formData.period_group}
                  onChange={(e) => setFormData({ ...formData, period_group: e.target.value })}
                  className="input"
                  required
                >
                  <option value="A">Group A</option>
                  <option value="B">Group B</option>
                </select>
              </div>
            )}

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="label">Start Date</label>
                <input
                  type="date"
                  value={formData.start_date}
                  onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
                  className="input"
                  required
                />
              </div>
              <div>
                <label className="label">End Date</label>
                <input
                  type="date"
                  value={formData.end_date}
                  onChange={(e) => setFormData({ ...formData, end_date: e.target.value })}
                  className="input"
                  required
                />
              </div>
            </div>

            <div>
              <label className="label">Payroll Run Date</label>
              <input
                type="date"
                value={formData.payroll_run_date}
                onChange={(e) => setFormData({ ...formData, payroll_run_date: e.target.value })}
                className="input"
              />
            </div>

            <div className="flex gap-2">
              <button type="button" onClick={resetForm} className="btn-secondary flex-1">
                Cancel
              </button>
              <button
                type="submit"
                disabled={createMutation.isPending || updateMutation.isPending}
                className="btn-primary flex-1"
              >
                {createMutation.isPending || updateMutation.isPending
                  ? 'Saving...'
                  : editingPeriod
                  ? 'Update'
                  : 'Add Period'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* List */}
      <div className="space-y-3">
        {payPeriods?.map((pp) => (
          <div key={pp.id} className="card p-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 text-xs font-medium bg-blue-100 text-blue-800 rounded-full">
                    Group {pp.period_group}
                  </span>
                  <span
                    className={`px-2 py-0.5 text-xs font-medium rounded-full ${
                      statusColors[pp.status] || 'bg-gray-100 text-gray-800'
                    }`}
                  >
                    {pp.status.charAt(0).toUpperCase() + pp.status.slice(1)}
                  </span>
                </div>
                <p className="font-medium text-gray-900 mt-1">
                  {format(parseISO(pp.start_date), 'MMM d, yyyy')} &ndash;{' '}
                  {format(parseISO(pp.end_date), 'MMM d, yyyy')}
                </p>
                {pp.payroll_run_date && (
                  <p className="text-xs text-gray-500">
                    Payroll run: {format(parseISO(pp.payroll_run_date), 'MMM d, yyyy')}
                  </p>
                )}
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleEdit(pp)}
                  className="p-2 text-gray-500 hover:text-primary-600 hover:bg-gray-100 rounded-lg"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                  </svg>
                </button>
                {pp.status === 'open' && (
                  confirmClose === pp.id ? (
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => closeMutation.mutate(pp.id)}
                        className="px-2 py-1 text-xs bg-red-600 text-white rounded"
                      >
                        Confirm
                      </button>
                      <button
                        onClick={() => setConfirmClose(null)}
                        className="px-2 py-1 text-xs bg-gray-200 text-gray-700 rounded"
                      >
                        Cancel
                      </button>
                    </div>
                  ) : (
                    <button
                      onClick={() => setConfirmClose(pp.id)}
                      className="px-2 py-1 text-xs bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
                    >
                      Close
                    </button>
                  )
                )}
              </div>
            </div>
          </div>
        ))}
        {payPeriods?.length === 0 && (
          <p className="text-center py-8 text-gray-500">No pay periods found. Generate some to get started.</p>
        )}
      </div>
    </div>
  )
}
