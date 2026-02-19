import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { format, parseISO } from 'date-fns'
import { useAuth } from '../contexts/AuthContext'
import * as api from '../services/api'

export default function Dashboard() {
  const { user } = useAuth()

  const { data: timesheet, isLoading: loadingTimesheet } = useQuery({
    queryKey: ['currentTimesheet'],
    queryFn: api.getCurrentTimesheet,
  })

  const { data: payPeriod } = useQuery({
    queryKey: ['currentPayPeriod'],
    queryFn: api.getCurrentPayPeriod,
  })

  const { data: entries } = useQuery({
    queryKey: ['timeEntries', timesheet?.id],
    queryFn: () => api.getTimeEntries(timesheet!.id),
    enabled: !!timesheet?.id,
  })

  const totalHours = entries?.reduce((sum, entry) => sum + Number(entry.hours), 0) || 0

  const statusColors = {
    draft: 'bg-gray-100 text-gray-800',
    submitted: 'bg-yellow-100 text-yellow-800',
    approved: 'bg-green-100 text-green-800',
    rejected: 'bg-red-100 text-red-800',
  }

  return (
    <div className="space-y-6">
      {/* Greeting */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900">
          Hi, {user?.first_name}!
        </h2>
        <p className="text-gray-600">
          {payPeriod
            ? `Pay period: ${format(parseISO(payPeriod.start_date), 'MMM d')} - ${format(parseISO(payPeriod.end_date), 'MMM d, yyyy')}`
            : 'Loading pay period...'}
        </p>
      </div>

      {/* Current Timesheet Summary */}
      <div className="card p-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold text-gray-900">Current Timesheet</h3>
          {timesheet && (
            <span
              className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${
                statusColors[timesheet.status]
              }`}
            >
              {timesheet.status.charAt(0).toUpperCase() + timesheet.status.slice(1)}
            </span>
          )}
        </div>

        {loadingTimesheet ? (
          <div className="flex justify-center py-4">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary-600"></div>
          </div>
        ) : (
          <>
            <div className="text-center py-4">
              <p className="text-4xl font-bold text-primary-600">{totalHours.toFixed(1)}</p>
              <p className="text-gray-500">hours logged</p>
            </div>

            <div className="grid grid-cols-2 gap-2 mt-4">
              <Link
                to="/entry"
                className="btn-primary text-center"
              >
                Add Time
              </Link>
              <Link
                to={`/timesheets/${timesheet?.id}`}
                className="btn-secondary text-center"
              >
                View Details
              </Link>
            </div>
          </>
        )}
      </div>

      {/* Quick Actions */}
      <div className="card p-4">
        <h3 className="font-semibold text-gray-900 mb-4">Quick Actions</h3>
        <div className="space-y-2">
          <Link
            to="/entry"
            className="flex items-center gap-3 p-3 rounded-lg hover:bg-gray-50 transition-colors"
          >
            <div className="bg-primary-100 p-2 rounded-lg">
              <svg className="w-5 h-5 text-primary-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
              </svg>
            </div>
            <div>
              <p className="font-medium text-gray-900">Log Time</p>
              <p className="text-sm text-gray-500">Add hours for today</p>
            </div>
          </Link>

          <Link
            to="/timesheets"
            className="flex items-center gap-3 p-3 rounded-lg hover:bg-gray-50 transition-colors"
          >
            <div className="bg-gray-100 p-2 rounded-lg">
              <svg className="w-5 h-5 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
            </div>
            <div>
              <p className="font-medium text-gray-900">View Timesheets</p>
              <p className="text-sm text-gray-500">See all your timesheets</p>
            </div>
          </Link>

          <Link
            to="/pto"
            className="flex items-center gap-3 p-3 rounded-lg hover:bg-gray-50 transition-colors"
          >
            <div className="bg-green-100 p-2 rounded-lg">
              <svg className="w-5 h-5 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
            </div>
            <div>
              <p className="font-medium text-gray-900">Add PTO</p>
              <p className="text-sm text-gray-500">Log time off</p>
            </div>
          </Link>
        </div>
      </div>

      {/* Manager/Admin Actions */}
      {(user?.is_manager || user?.is_admin) && (
        <div className="card p-4">
          <h3 className="font-semibold text-gray-900 mb-4">Admin Tools</h3>
          <div className="space-y-2">
            <Link
              to="/reports"
              className="flex items-center gap-3 p-3 rounded-lg hover:bg-gray-50 transition-colors"
            >
              <div className="bg-purple-100 p-2 rounded-lg">
                <svg className="w-5 h-5 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <div>
                <p className="font-medium text-gray-900">Reports</p>
                <p className="text-sm text-gray-500">Export payroll and billing</p>
              </div>
            </Link>

            {user?.is_admin && (
              <>
                <Link
                  to="/employees"
                  className="flex items-center gap-3 p-3 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  <div className="bg-orange-100 p-2 rounded-lg">
                    <svg className="w-5 h-5 text-orange-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                    </svg>
                  </div>
                  <div>
                    <p className="font-medium text-gray-900">Employees</p>
                    <p className="text-sm text-gray-500">Manage employee accounts</p>
                  </div>
                </Link>

                <Link
                  to="/clients"
                  className="flex items-center gap-3 p-3 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  <div className="bg-teal-100 p-2 rounded-lg">
                    <svg className="w-5 h-5 text-teal-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                    </svg>
                  </div>
                  <div>
                    <p className="font-medium text-gray-900">Clients</p>
                    <p className="text-sm text-gray-500">Manage clients</p>
                  </div>
                </Link>

                <Link
                  to="/service-types"
                  className="flex items-center gap-3 p-3 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  <div className="bg-indigo-100 p-2 rounded-lg">
                    <svg className="w-5 h-5 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
                    </svg>
                  </div>
                  <div>
                    <p className="font-medium text-gray-900">Service Types</p>
                    <p className="text-sm text-gray-500">Manage service types</p>
                  </div>
                </Link>

                <Link
                  to="/locations"
                  className="flex items-center gap-3 p-3 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  <div className="bg-rose-100 p-2 rounded-lg">
                    <svg className="w-5 h-5 text-rose-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                    </svg>
                  </div>
                  <div>
                    <p className="font-medium text-gray-900">Locations</p>
                    <p className="text-sm text-gray-500">Manage locations & job codes</p>
                  </div>
                </Link>

                <Link
                  to="/pay-periods"
                  className="flex items-center gap-3 p-3 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  <div className="bg-amber-100 p-2 rounded-lg">
                    <svg className="w-5 h-5 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                    </svg>
                  </div>
                  <div>
                    <p className="font-medium text-gray-900">Pay Periods</p>
                    <p className="text-sm text-gray-500">Manage pay period schedules</p>
                  </div>
                </Link>
              </>
            )}
          </div>
        </div>
      )}

      {/* Rejected Timesheet Alert */}
      {timesheet?.status === 'rejected' && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4">
          <div className="flex items-start gap-3">
            <svg className="w-5 h-5 text-red-600 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <div>
              <p className="font-medium text-red-800">Timesheet Rejected</p>
              <p className="text-sm text-red-700 mt-1">
                {timesheet.rejection_reason || 'Please review and resubmit your timesheet.'}
              </p>
              <Link
                to={`/timesheets/${timesheet.id}`}
                className="text-sm font-medium text-red-800 underline mt-2 inline-block"
              >
                Review and fix
              </Link>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
