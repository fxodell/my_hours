import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { format, parseISO } from 'date-fns'
import * as api from '../services/api'

const statusColors = {
  draft: 'bg-gray-100 text-gray-800',
  submitted: 'bg-yellow-100 text-yellow-800',
  approved: 'bg-green-100 text-green-800',
  rejected: 'bg-red-100 text-red-800',
}

export default function Timesheets() {
  const { data: timesheets, isLoading } = useQuery({
    queryKey: ['timesheets'],
    queryFn: () => api.getTimesheets(),
  })

  const { data: payPeriods } = useQuery({
    queryKey: ['payPeriods'],
    queryFn: () => api.getPayPeriods(20),
  })

  // Create a map of pay period IDs to pay periods for easy lookup
  const payPeriodMap = new Map(payPeriods?.map((pp) => [pp.id, pp]))

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-gray-900">My Timesheets</h2>

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
              <Link
                key={timesheet.id}
                to={`/timesheets/${timesheet.id}`}
                className="card p-4 block hover:shadow-md transition-shadow"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-gray-900">
                      {payPeriod
                        ? `${format(parseISO(payPeriod.start_date), 'MMM d')} - ${format(parseISO(payPeriod.end_date), 'MMM d, yyyy')}`
                        : 'Pay Period'}
                    </p>
                    <p className="text-sm text-gray-500">
                      Updated {format(parseISO(timesheet.updated_at), 'MMM d, h:mm a')}
                    </p>
                  </div>
                  <span
                    className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      statusColors[timesheet.status]
                    }`}
                  >
                    {timesheet.status.charAt(0).toUpperCase() + timesheet.status.slice(1)}
                  </span>
                </div>

                {timesheet.status === 'rejected' && timesheet.rejection_reason && (
                  <div className="mt-2 text-sm text-red-600 bg-red-50 p-2 rounded">
                    Rejected: {timesheet.rejection_reason}
                  </div>
                )}
              </Link>
            )
          })}
        </div>
      )}
    </div>
  )
}
