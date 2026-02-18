import { useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { format, parseISO } from 'date-fns'
import * as api from '../services/api'
import type { TimeEntry, PTOEntry } from '../types'

const statusColors = {
  draft: 'bg-gray-100 text-gray-800',
  submitted: 'bg-yellow-100 text-yellow-800',
  approved: 'bg-green-100 text-green-800',
  rejected: 'bg-red-100 text-red-800',
}

export default function TimesheetDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null)
  const [deletePTOConfirm, setDeletePTOConfirm] = useState<string | null>(null)

  const { data: timesheet, isLoading } = useQuery({
    queryKey: ['timesheet', id],
    queryFn: () => api.getTimesheet(id!),
    enabled: !!id,
  })

  const { data: entries } = useQuery({
    queryKey: ['timeEntries', id],
    queryFn: () => api.getTimeEntries(id!),
    enabled: !!id,
  })

  const { data: ptoEntries } = useQuery({
    queryKey: ['ptoEntries', id],
    queryFn: () => api.getPTOEntries(id!),
    enabled: !!id,
  })

  const { data: payPeriod } = useQuery({
    queryKey: ['payPeriod', timesheet?.pay_period_id],
    queryFn: () => api.getCurrentPayPeriod(),
    enabled: !!timesheet?.pay_period_id,
  })

  const { data: clients } = useQuery({
    queryKey: ['clients'],
    queryFn: api.getClients,
  })

  const { data: serviceTypes } = useQuery({
    queryKey: ['serviceTypes'],
    queryFn: api.getServiceTypes,
  })

  const clientMap = new Map(clients?.map((c) => [c.id, c]))
  const serviceTypeMap = new Map(serviceTypes?.map((st) => [st.id, st]))

  const submitMutation = useMutation({
    mutationFn: () => api.submitTimesheet(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['timesheet', id] })
      queryClient.invalidateQueries({ queryKey: ['timesheets'] })
      queryClient.invalidateQueries({ queryKey: ['currentTimesheet'] })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (entryId: string) => api.deleteTimeEntry(id!, entryId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['timeEntries', id] })
      setDeleteConfirm(null)
    },
  })

  const deletePTOMutation = useMutation({
    mutationFn: (entryId: string) => api.deletePTOEntry(id!, entryId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ptoEntries', id] })
      setDeletePTOConfirm(null)
    },
  })

  const totalWorkHours = entries?.reduce((sum, entry) => sum + Number(entry.hours), 0) || 0
  const totalPTOHours = ptoEntries?.reduce((sum, entry) => sum + Number(entry.hours), 0) || 0
  const totalHours = totalWorkHours + totalPTOHours
  const canEdit = timesheet?.status === 'draft' || timesheet?.status === 'rejected'
  const canSubmit = canEdit && ((entries?.length ?? 0) > 0 || (ptoEntries?.length ?? 0) > 0)

  // Group entries by date
  const entriesByDate = entries?.reduce((acc, entry) => {
    const date = entry.work_date
    if (!acc[date]) acc[date] = []
    acc[date].push(entry)
    return acc
  }, {} as Record<string, TimeEntry[]>)

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  if (!timesheet) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">Timesheet not found</p>
        <button onClick={() => navigate(-1)} className="btn-secondary mt-4">
          Go Back
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-gray-900">Timesheet</h2>
          <p className="text-gray-500 text-sm">
            {payPeriod
              ? `${format(parseISO(payPeriod.start_date), 'MMM d')} - ${format(parseISO(payPeriod.end_date), 'MMM d, yyyy')}`
              : 'Loading...'}
          </p>
        </div>
        <span
          className={`px-3 py-1 rounded-full text-sm font-medium ${
            statusColors[timesheet.status]
          }`}
        >
          {timesheet.status.charAt(0).toUpperCase() + timesheet.status.slice(1)}
        </span>
      </div>

      {/* Rejection reason */}
      {timesheet.status === 'rejected' && timesheet.rejection_reason && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
          <p className="font-medium">Rejected</p>
          <p className="text-sm mt-1">{timesheet.rejection_reason}</p>
        </div>
      )}

      {/* Summary Card */}
      <div className="card p-4">
        <div className="text-center mb-2">
          <p className="text-4xl font-bold text-primary-600">{totalHours.toFixed(1)}</p>
          <p className="text-gray-500">total hours</p>
        </div>
        {(totalWorkHours > 0 || totalPTOHours > 0) && (
          <div className="flex justify-center gap-4 text-sm text-gray-500 border-t pt-2">
            <span>Work: {totalWorkHours.toFixed(1)}h</span>
            <span>PTO: {totalPTOHours.toFixed(1)}h</span>
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="flex gap-2">
        {canEdit && (
          <>
            <Link to="/entry" className="btn-primary flex-1">
              Add Time
            </Link>
            <Link to="/pto" className="btn-secondary flex-1">
              Add PTO
            </Link>
          </>
        )}
      </div>
      {canSubmit && (
        <button
          onClick={() => submitMutation.mutate()}
          disabled={submitMutation.isPending}
          className="btn-success w-full"
        >
          {submitMutation.isPending ? 'Submitting...' : 'Submit for Approval'}
        </button>
      )}

      {/* Entries by date */}
      {entries?.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          <p>No time entries yet.</p>
          <Link to="/entry" className="btn-primary mt-4 inline-block">
            Add Your First Entry
          </Link>
        </div>
      ) : (
        <div className="space-y-4">
          {Object.entries(entriesByDate || {})
            .sort(([a], [b]) => b.localeCompare(a))
            .map(([date, dayEntries]) => (
              <div key={date}>
                <h3 className="font-medium text-gray-900 mb-2">
                  {format(parseISO(date), 'EEEE, MMM d')}
                </h3>
                <div className="space-y-2">
                  {dayEntries.map((entry) => (
                    <div key={entry.id} className="card p-3">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <span className="font-medium">
                              {entry.hours}h
                            </span>
                            <span className="text-gray-400">•</span>
                            <span className="text-gray-600">
                              {entry.client_id
                                ? clientMap.get(entry.client_id)?.name
                                : 'No client'}
                            </span>
                          </div>
                          <p className="text-sm text-gray-500 mt-0.5">
                            {entry.service_type_id
                              ? serviceTypeMap.get(entry.service_type_id)?.name
                              : 'No service type'}
                            {' • '}
                            {entry.work_mode === 'remote' ? 'Remote' : 'On-Site'}
                          </p>
                          {entry.description && (
                            <p className="text-sm text-gray-600 mt-1 line-clamp-2">
                              {entry.description}
                            </p>
                          )}
                        </div>
                        {canEdit && (
                          <div className="flex items-center gap-1">
                            <Link
                              to={`/timesheets/${id}/entries/${entry.id}/edit`}
                              className="text-gray-400 hover:text-primary-500 p-1"
                            >
                              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                              </svg>
                            </Link>
                            <button
                              onClick={() => setDeleteConfirm(entry.id)}
                              className="text-gray-400 hover:text-red-500 p-1"
                            >
                              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                              </svg>
                            </button>
                          </div>
                        )}
                      </div>

                      {/* Delete confirmation */}
                      {deleteConfirm === entry.id && (
                        <div className="mt-3 pt-3 border-t border-gray-200 flex items-center justify-between">
                          <span className="text-sm text-gray-600">Delete this entry?</span>
                          <div className="flex gap-2">
                            <button
                              onClick={() => setDeleteConfirm(null)}
                              className="btn-secondary text-sm py-1 px-3"
                            >
                              Cancel
                            </button>
                            <button
                              onClick={() => deleteMutation.mutate(entry.id)}
                              disabled={deleteMutation.isPending}
                              className="btn-danger text-sm py-1 px-3"
                            >
                              Delete
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ))}
        </div>
      )}

      {/* PTO Entries */}
      {ptoEntries && ptoEntries.length > 0 && (
        <div className="space-y-4">
          <h3 className="font-semibold text-gray-900">PTO Entries</h3>
          <div className="space-y-2">
            {ptoEntries.map((entry) => (
              <div key={entry.id} className="card p-3 bg-green-50 border-green-200">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{entry.hours}h</span>
                      <span className="text-gray-400">•</span>
                      <span className="text-gray-600 capitalize">{entry.pto_type.replace('_', ' ')}</span>
                    </div>
                    <p className="text-sm text-gray-500 mt-0.5">
                      {format(parseISO(entry.pto_date), 'EEEE, MMM d')}
                    </p>
                    {entry.notes && (
                      <p className="text-sm text-gray-600 mt-1">{entry.notes}</p>
                    )}
                  </div>
                  {canEdit && (
                    <div className="flex items-center gap-1">
                      <Link
                        to={`/timesheets/${id}/pto/${entry.id}/edit`}
                        className="text-gray-400 hover:text-primary-500 p-1"
                      >
                        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                        </svg>
                      </Link>
                      <button
                        onClick={() => setDeletePTOConfirm(entry.id)}
                        className="text-gray-400 hover:text-red-500 p-1"
                      >
                        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </div>
                  )}
                </div>

                {/* Delete confirmation */}
                {deletePTOConfirm === entry.id && (
                  <div className="mt-3 pt-3 border-t border-green-200 flex items-center justify-between">
                    <span className="text-sm text-gray-600">Delete this PTO entry?</span>
                    <div className="flex gap-2">
                      <button
                        onClick={() => setDeletePTOConfirm(null)}
                        className="btn-secondary text-sm py-1 px-3"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={() => deletePTOMutation.mutate(entry.id)}
                        disabled={deletePTOMutation.isPending}
                        className="btn-danger text-sm py-1 px-3"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
