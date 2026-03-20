import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '../contexts/AuthContext'
import * as api from '../services/api'
import type { SiteRequest } from '../types'

const statusBadge = (status: string) => {
  switch (status) {
    case 'pending':
      return 'bg-yellow-100 text-yellow-800'
    case 'approved':
      return 'bg-green-100 text-green-800'
    case 'rejected':
      return 'bg-red-100 text-red-800'
    default:
      return 'bg-gray-100 text-gray-800'
  }
}

export default function SiteRequests() {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const isManager = user?.is_manager || user?.is_admin
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [showRejectModal, setShowRejectModal] = useState<string | null>(null)
  const [rejectionReason, setRejectionReason] = useState('')

  const { data: requests, isLoading } = useQuery({
    queryKey: ['siteRequests', statusFilter],
    queryFn: () => api.getSiteRequests(statusFilter || undefined),
  })

  const approveMutation = useMutation({
    mutationFn: api.approveSiteRequest,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['siteRequests'] })
    },
  })

  const rejectMutation = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) =>
      api.rejectSiteRequest(id, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['siteRequests'] })
      setShowRejectModal(null)
      setRejectionReason('')
    },
  })

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Site Requests</h2>
        <Link to="/site-requests/new" className="btn btn-primary text-sm">
          Request New Site
        </Link>
      </div>

      {/* Status filter */}
      <div className="flex gap-2">
        {['', 'pending', 'approved', 'rejected'].map((s) => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            className={`px-3 py-1 rounded-full text-sm ${
              statusFilter === s
                ? 'bg-primary-600 text-white'
                : 'bg-gray-100 text-gray-600'
            }`}
          >
            {s || 'All'}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="flex justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
        </div>
      ) : !requests?.length ? (
        <div className="text-center py-8 text-gray-500">
          <p>No site requests found.</p>
          <Link to="/site-requests/new" className="text-primary-600 mt-2 inline-block">
            Submit your first request
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          {requests.map((req: SiteRequest) => (
            <div key={req.id} className="bg-white rounded-xl border border-gray-200 p-4 space-y-2">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="font-medium text-gray-900">{req.site_name}</h3>
                  <p className="text-sm text-gray-500">
                    {req.client_name}
                    {req.region && ` — ${req.region}`}
                  </p>
                </div>
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${statusBadge(req.status)}`}>
                  {req.status}
                </span>
              </div>

              {req.job_code && (
                <p className="text-sm text-gray-600">
                  AFE: {req.job_code}
                  {req.job_code_description && ` — ${req.job_code_description}`}
                </p>
              )}

              {req.notes && (
                <p className="text-sm text-gray-500">{req.notes}</p>
              )}

              {isManager && req.employee_name && (
                <p className="text-xs text-gray-400">Requested by {req.employee_name}</p>
              )}

              <p className="text-xs text-gray-400">
                {new Date(req.created_at).toLocaleDateString()}
              </p>

              {req.status === 'rejected' && req.rejection_reason && (
                <div className="bg-red-50 border border-red-200 rounded p-2 text-sm text-red-700">
                  Reason: {req.rejection_reason}
                </div>
              )}

              {req.status === 'approved' && req.reviewer_name && (
                <p className="text-xs text-green-600">
                  Approved by {req.reviewer_name}
                </p>
              )}

              {/* Manager actions for pending requests */}
              {isManager && req.status === 'pending' && (
                <div className="flex gap-2 pt-2">
                  <button
                    onClick={() => approveMutation.mutate(req.id)}
                    disabled={approveMutation.isPending}
                    className="btn-primary flex-1 text-sm"
                  >
                    {approveMutation.isPending ? 'Approving...' : 'Approve'}
                  </button>
                  <button
                    onClick={() => setShowRejectModal(req.id)}
                    className="btn-danger flex-1 text-sm"
                  >
                    Reject
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Reject Modal */}
      {showRejectModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-md">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              Reject Site Request
            </h3>
            <div className="mb-4">
              <label className="label">Reason for rejection</label>
              <textarea
                value={rejectionReason}
                onChange={(e) => setRejectionReason(e.target.value)}
                className="input min-h-[100px]"
                placeholder="Please explain why this request is being rejected..."
              />
            </div>
            <div className="flex gap-3">
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
