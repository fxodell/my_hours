import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { format, parseISO } from 'date-fns'
import * as api from '../services/api'
import type { Timesheet, TimeEntry, User } from '../types'

export default function Approvals() {
  const queryClient = useQueryClient()
  const [selectedTimesheet, setSelectedTimesheet] = useState<string | null>(null)
  const [rejectionReason, setRejectionReason] = useState('')
  const [showRejectModal, setShowRejectModal] = useState<string | null>(null)

  const { data: pendingTimesheets, isLoading } = useQuery({
    queryKey: ['timesheets', 'submitted'],
    queryFn: () => api.getTimesheets({ status: 'submitted' }),
  })

  const { data: employees } = useQuery({
    queryKey: ['employees'],
    queryFn: api.getEmployees,
  })

  const { data: payPeriods } = useQuery({
    queryKey: ['payPeriods'],
    queryFn: () => api.getPayPeriods(20),
  })

  const { data: selectedEntries } = useQuery({
    queryKey: ['timeEntries', selectedTimesheet],
    queryFn: () => api.getTimeEntries(selectedTimesheet!),
    enabled: !!selectedTimesheet,
  })

  const { data: clients } = useQuery({
    queryKey: ['clients'],
    queryFn: api.getClients,
  })

  const { data: serviceTypes } = useQuery({
    queryKey: ['serviceTypes'],
    queryFn: api.getServiceTypes,
  })

  const employeeMap = new Map(employees?.map((e) => [e.id, e]))
  const payPeriodMap = new Map(payPeriods?.map((pp) => [pp.id, pp]))
  const clientMap = new Map(clients?.map((c) => [c.id, c]))
  const serviceTypeMap = new Map(serviceTypes?.map((st) => [st.id, st]))

  const approveMutation = useMutation({
    mutationFn: (id: string) => api.approveTimesheet(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['timesheets'] })
      setSelectedTimesheet(null)
    },
  })

  const rejectMutation = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) =>
      api.rejectTimesheet(id, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['timesheets'] })
      setShowRejectModal(null)
      setRejectionReason('')
      setSelectedTimesheet(null)
    },
  })

  const getTotalHours = (entries: TimeEntry[] | undefined) =>
    entries?.reduce((sum, entry) => sum + Number(entry.hours), 0) || 0

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-gray-900">Pending Approvals</h2>

      {pendingTimesheets?.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          <svg className="w-12 h-12 mx-auto text-gray-400 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p>No timesheets pending approval.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {pendingTimesheets?.map((timesheet) => {
            const employee = employeeMap.get(timesheet.employee_id)
            const payPeriod = payPeriodMap.get(timesheet.pay_period_id)
            const isSelected = selectedTimesheet === timesheet.id

            return (
              <div key={timesheet.id} className="card overflow-hidden">
                {/* Timesheet Header */}
                <button
                  onClick={() => setSelectedTimesheet(isSelected ? null : timesheet.id)}
                  className="w-full p-4 text-left hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium text-gray-900">
                        {employee?.full_name || 'Unknown Employee'}
                      </p>
                      <p className="text-sm text-gray-500">
                        {payPeriod
                          ? `${format(parseISO(payPeriod.start_date), 'MMM d')} - ${format(parseISO(payPeriod.end_date), 'MMM d')}`
                          : 'Unknown Period'}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-gray-500">
                        Submitted {format(parseISO(timesheet.submitted_at!), 'MMM d')}
                      </span>
                      <svg
                        className={`w-5 h-5 text-gray-400 transition-transform ${isSelected ? 'rotate-180' : ''}`}
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                      </svg>
                    </div>
                  </div>
                </button>

                {/* Expanded Details */}
                {isSelected && (
                  <div className="border-t border-gray-200 p-4 bg-gray-50">
                    {/* Summary */}
                    <div className="mb-4 text-center">
                      <p className="text-2xl font-bold text-primary-600">
                        {getTotalHours(selectedEntries).toFixed(1)}
                      </p>
                      <p className="text-sm text-gray-500">total hours</p>
                    </div>

                    {/* Entries */}
                    <div className="space-y-2 mb-4 max-h-60 overflow-y-auto">
                      {selectedEntries?.map((entry) => (
                        <div key={entry.id} className="bg-white p-2 rounded border border-gray-200">
                          <div className="flex items-center justify-between text-sm">
                            <span>{format(parseISO(entry.work_date), 'EEE, MMM d')}</span>
                            <span className="font-medium">{entry.hours}h</span>
                          </div>
                          <p className="text-xs text-gray-500 mt-0.5">
                            {entry.client_id ? clientMap.get(entry.client_id)?.name : 'No client'}
                            {' • '}
                            {entry.service_type_id ? serviceTypeMap.get(entry.service_type_id)?.name : 'No service'}
                          </p>
                          {entry.description && (
                            <p className="text-xs text-gray-600 mt-1 line-clamp-1">
                              {entry.description}
                            </p>
                          )}
                        </div>
                      ))}
                    </div>

                    {/* Actions */}
                    <div className="flex gap-2">
                      <button
                        onClick={() => approveMutation.mutate(timesheet.id)}
                        disabled={approveMutation.isPending}
                        className="btn-success flex-1"
                      >
                        {approveMutation.isPending ? 'Approving...' : 'Approve'}
                      </button>
                      <button
                        onClick={() => setShowRejectModal(timesheet.id)}
                        className="btn-danger flex-1"
                      >
                        Reject
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      {/* Reject Modal */}
      {showRejectModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-md">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              Reject Timesheet
            </h3>
            <div className="mb-4">
              <label className="label">Reason for rejection</label>
              <textarea
                value={rejectionReason}
                onChange={(e) => setRejectionReason(e.target.value)}
                className="input min-h-[100px]"
                placeholder="Please explain why this timesheet is being rejected..."
              />
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => {
                  setShowRejectModal(null)
                  setRejectionReason('')
                }}
                className="btn-secondary flex-1"
              >
                Cancel
              </button>
              <button
                onClick={() =>
                  rejectMutation.mutate({
                    id: showRejectModal,
                    reason: rejectionReason,
                  })
                }
                disabled={!rejectionReason.trim() || rejectMutation.isPending}
                className="btn-danger flex-1"
              >
                {rejectMutation.isPending ? 'Rejecting...' : 'Reject'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
