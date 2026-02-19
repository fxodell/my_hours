import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { format, parseISO } from 'date-fns'
import * as api from '../services/api'
import { useAuth } from '../contexts/AuthContext'

const statusColors = {
  draft: 'bg-gray-100 text-gray-800',
  submitted: 'bg-yellow-100 text-yellow-800',
  approved: 'bg-green-100 text-green-800',
  rejected: 'bg-red-100 text-red-800',
}

export default function Timesheets() {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null)

  const { data: timesheets, isLoading } = useQuery({
    queryKey: ['timesheets'],
    queryFn: () => api.getTimesheets(),
  })

  const { data: payPeriods } = useQuery({
    queryKey: ['payPeriods'],
    queryFn: () => api.getPayPeriods(20),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteTimesheet(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['timesheets'] })
      setConfirmDelete(null)
    },
  })

  const reopenMutation = useMutation({
    mutationFn: (id: string) => api.reopenTimesheet(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['timesheets'] })
    },
  })

  const payPeriodMap = new Map(payPeriods?.map((pp) => [pp.id, pp]))
  const isManager = user?.is_manager || user?.is_admin

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-gray-900">
        {isManager ? 'All Timesheets' : 'My Timesheets'}
      </h2>

      {timesheets?.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          <p>No timesheets yet.</p>
          <Link to="/entry" className="btn-primary mt-4 inline-block">
            Create Your First Entry
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          {timesheets?.map((timesheet) => {
            const payPeriod = payPeriodMap.get(timesheet.pay_period_id)
            return (
              <div
                key={timesheet.id}
                className="card p-4 block"
              >
                <div className="flex items-center justify-between">
                  <Link
                    to={`/timesheets/${timesheet.id}`}
                    className="flex-1 hover:opacity-75 transition-opacity"
                  >
                    <div>
                      {isManager && timesheet.employee_name && (
                        <p className="font-semibold text-gray-900">
                          {timesheet.employee_name}
                        </p>
                      )}
                      <p className={`${isManager && timesheet.employee_name ? 'text-sm text-gray-600' : 'font-medium text-gray-900'}`}>
                        {payPeriod
                          ? `${format(parseISO(payPeriod.start_date), 'MMM d')} - ${format(parseISO(payPeriod.end_date), 'MMM d, yyyy')}`
                          : 'Pay Period'}
                      </p>
                      <p className="text-sm text-gray-500">
                        Updated {format(parseISO(timesheet.updated_at), 'MMM d, h:mm a')}
                      </p>
                    </div>
                  </Link>
                  <div className="flex items-center gap-2 ml-3">
                    <span
                      className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        statusColors[timesheet.status]
                      }`}
                    >
                      {timesheet.status.charAt(0).toUpperCase() + timesheet.status.slice(1)}
                    </span>
                  </div>
                </div>

                {timesheet.status === 'rejected' && timesheet.rejection_reason && (
                  <div className="mt-2 text-sm text-red-600 bg-red-50 p-2 rounded">
                    Rejected: {timesheet.rejection_reason}
                  </div>
                )}

                {/* Manager actions */}
                {isManager && (
                  <div className="mt-3 flex gap-2 border-t pt-3">
                    {(timesheet.status === 'approved' || timesheet.status === 'submitted') && (
                      <button
                        onClick={() => reopenMutation.mutate(timesheet.id)}
                        disabled={reopenMutation.isPending}
                        className="text-sm px-3 py-1.5 rounded-lg border border-blue-300 text-blue-700 hover:bg-blue-50 transition-colors"
                      >
                        {reopenMutation.isPending ? 'Reopening...' : 'Reopen as Draft'}
                      </button>
                    )}
                    {confirmDelete === timesheet.id ? (
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-red-600">Delete?</span>
                        <button
                          onClick={() => deleteMutation.mutate(timesheet.id)}
                          disabled={deleteMutation.isPending}
                          className="text-sm px-3 py-1.5 rounded-lg bg-red-600 text-white hover:bg-red-700 transition-colors"
                        >
                          {deleteMutation.isPending ? 'Deleting...' : 'Confirm'}
                        </button>
                        <button
                          onClick={() => setConfirmDelete(null)}
                          className="text-sm px-3 py-1.5 rounded-lg border border-gray-300 text-gray-600 hover:bg-gray-50 transition-colors"
                        >
                          Cancel
                        </button>
                      </div>
                    ) : (
                      <button
                        onClick={() => setConfirmDelete(timesheet.id)}
                        className="text-sm px-3 py-1.5 rounded-lg border border-red-300 text-red-700 hover:bg-red-50 transition-colors"
                      >
                        Delete
                      </button>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
