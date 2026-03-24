import { useState, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { format, parseISO, differenceInCalendarDays } from 'date-fns'
import * as api from '../services/api'
import { getEntryDateMax, isTimesheetEditable, isTimesheetReadOnly } from '../timesheetStatus'

const PTO_TYPES = [
  { value: 'personal', label: 'Personal Time Off' },
  { value: 'sick', label: 'Sick Leave' },
  { value: 'holiday', label: 'Holiday' },
  { value: 'other', label: 'Other' },
]

const HOUR_OPTIONS = [1, 2, 3, 4, 5, 6, 7, 8]

interface FormData {
  pto_date: string
  pto_type: 'personal' | 'sick' | 'holiday' | 'other'
  hours: number
  notes: string
}

export default function PTOEntry() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [searchParams] = useSearchParams()
  const timesheetParam = searchParams.get('timesheet')
  const [error, setError] = useState('')
  const [selectedPeriodId, setSelectedPeriodId] = useState<string | null>(null)

  // Fetch recent pay periods when no specific timesheet is targeted
  const { data: recentPeriods } = useQuery({
    queryKey: ['recentPayPeriods'],
    queryFn: api.getRecentPayPeriods,
    enabled: !timesheetParam,
  })

  // Determine which period is "current" (contains today)
  useEffect(() => {
    if (recentPeriods && recentPeriods.length > 0 && !selectedPeriodId) {
      const today = format(new Date(), 'yyyy-MM-dd')
      const current = recentPeriods.find(
        (pp) => pp.start_date <= today && pp.end_date >= today
      )
      setSelectedPeriodId(current?.id ?? recentPeriods[0].id)
    }
  }, [recentPeriods, selectedPeriodId])

  // When a specific timesheet is passed, use it directly; otherwise use period-based lookup
  const { data: timesheet } = useQuery({
    queryKey: timesheetParam
      ? ['timesheet', timesheetParam]
      : selectedPeriodId
        ? ['timesheetForPeriod', selectedPeriodId]
        : ['currentTimesheet'],
    queryFn: () =>
      timesheetParam
        ? api.getTimesheet(timesheetParam)
        : selectedPeriodId
          ? api.getTimesheetForPeriod(selectedPeriodId)
          : api.getCurrentTimesheet(),
    enabled: !!timesheetParam || !!selectedPeriodId,
  })

  const { data: payPeriod } = useQuery({
    queryKey: ['payPeriod', timesheet?.pay_period_id],
    queryFn: () => api.getPayPeriod(timesheet!.pay_period_id),
    enabled: !!timesheet?.pay_period_id,
  })
  const { data: billingWeeks } = useQuery({
    queryKey: ['billingWeeks', timesheet?.id],
    queryFn: () => api.getBillingWeeks(timesheet!.id),
    enabled: !!timesheet?.id,
  })

  const { register, handleSubmit, watch, formState: { errors } } = useForm<FormData>({
    defaultValues: {
      pto_date: format(new Date(), 'yyyy-MM-dd'),
      pto_type: 'personal',
      hours: 8,
      notes: '',
    },
  })

  const createPTOMutation = useMutation({
    mutationFn: (data: FormData) =>
      api.createPTOEntry(timesheet!.id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ptoEntries', timesheet!.id] })
      queryClient.invalidateQueries({ queryKey: ['timesheet', timesheet!.id] })
      queryClient.invalidateQueries({ queryKey: ['currentTimesheet'] })
      navigate('/')
    },
    onError: (err) => {
      setError(err instanceof Error ? err.message : 'Failed to create PTO entry')
    },
  })

  const onSubmit = (data: FormData) => {
    if (!timesheet) return
    createPTOMutation.mutate(data)
  }

  const canEdit = isTimesheetEditable(timesheet?.status)
  const maxPTODate = getEntryDateMax(payPeriod?.end_date)
  const selectedPtoDate = watch('pto_date')
  const selectedWeek = billingWeeks?.find((week) => week.week_start_date <= selectedPtoDate && week.week_end_date >= selectedPtoDate)
  const isSelectedWeekLocked = !!selectedWeek && (selectedWeek.status === 'approved' || selectedWeek.status === 'billed')
  const canEditForm = canEdit && !isSelectedWeekLocked

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-gray-900">Add PTO</h2>
        <button
          onClick={() => navigate(-1)}
          className="text-gray-500 hover:text-gray-700"
        >
          Cancel
        </button>
      </div>

      {isTimesheetReadOnly(timesheet?.status) && (
        <div className="bg-yellow-50 border border-yellow-200 text-yellow-800 px-4 py-3 rounded-lg text-sm">
          This timesheet is read-only and cannot be edited.
        </div>
      )}
      {isSelectedWeekLocked && (
        <div className="bg-yellow-50 border border-yellow-200 text-yellow-800 px-4 py-3 rounded-lg text-sm">
          The selected date is in a billing week marked {selectedWeek?.status}. PTO for this week is locked.
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        {/* Pay Period Selector */}
        {!timesheetParam && recentPeriods && recentPeriods.length > 1 && (
          <div>
            <label className="label">Pay Period</label>
            <div className="grid grid-cols-1 gap-2">
              {recentPeriods
                .slice()
                .sort((a, b) => b.start_date.localeCompare(a.start_date))
                .map((pp) => {
                  const today = format(new Date(), 'yyyy-MM-dd')
                  const isCurrentPeriod = pp.start_date <= today && pp.end_date >= today
                  const isClosed = pp.status === 'closed'
                  const graceDaysLeft = isClosed ? 7 - differenceInCalendarDays(new Date(), parseISO(pp.end_date)) : 0
                  return (
                    <label
                      key={pp.id}
                      className={`flex items-center justify-between p-3 rounded-lg border cursor-pointer transition-colors ${
                        selectedPeriodId === pp.id
                          ? 'bg-primary-100 border-primary-500 text-primary-700'
                          : 'border-gray-300 hover:border-gray-400'
                      }`}
                    >
                      <input
                        type="radio"
                        name="pay_period"
                        value={pp.id}
                        checked={selectedPeriodId === pp.id}
                        onChange={() => setSelectedPeriodId(pp.id)}
                        className="sr-only"
                      />
                      <span>
                        {format(parseISO(pp.start_date), 'MMM d')} - {format(parseISO(pp.end_date), 'MMM d, yyyy')}
                      </span>
                      <span className="flex gap-1">
                        {isCurrentPeriod && (
                          <span className="text-xs bg-primary-200 text-primary-800 px-2 py-0.5 rounded-full">Current</span>
                        )}
                        {isClosed && graceDaysLeft > 0 && (
                          <span className="text-xs bg-amber-100 text-amber-800 px-2 py-0.5 rounded-full">
                            {graceDaysLeft}d left
                          </span>
                        )}
                      </span>
                    </label>
                  )
                })}
            </div>
          </div>
        )}

        {/* Date */}
        <div>
          <label className="label">Date</label>
          <input
            type="date"
            {...register('pto_date', { required: 'Date is required' })}
            className="input"
            disabled={!canEditForm}
            min={payPeriod?.start_date}
            max={maxPTODate}
          />
          {payPeriod && (
            <p className="text-gray-500 text-xs mt-1">
              Valid dates: {payPeriod.start_date} to {maxPTODate ?? payPeriod.end_date}
            </p>
          )}
          {errors.pto_date && (
            <p className="text-red-500 text-sm mt-1">{errors.pto_date.message}</p>
          )}
        </div>

        {/* PTO Type */}
        <div>
          <label className="label">PTO Type</label>
          <div className="grid grid-cols-2 gap-2">
            {PTO_TYPES.map((type) => (
              <label
                key={type.value}
                className={`flex items-center justify-center p-3 rounded-lg border cursor-pointer transition-colors ${
                  watch('pto_type') === type.value
                    ? 'bg-primary-100 border-primary-500 text-primary-700'
                    : 'border-gray-300 hover:border-gray-400'
                } ${!canEditForm ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                <input
                  type="radio"
                  value={type.value}
                  {...register('pto_type')}
                  className="sr-only"
                  disabled={!canEditForm}
                />
                {type.label}
              </label>
            ))}
          </div>
        </div>

        {/* Hours */}
        <div>
          <label className="label">Hours</label>
          <div className="grid grid-cols-4 gap-2">
            {HOUR_OPTIONS.map((h) => (
              <label
                key={h}
                className={`flex items-center justify-center p-3 rounded-lg border cursor-pointer transition-colors ${
                  watch('hours') === h
                    ? 'bg-primary-100 border-primary-500 text-primary-700'
                    : 'border-gray-300 hover:border-gray-400'
                } ${!canEditForm ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                <input
                  type="radio"
                  value={h}
                  {...register('hours', { valueAsNumber: true })}
                  className="sr-only"
                  disabled={!canEditForm}
                />
                {h}
              </label>
            ))}
          </div>
        </div>

        {/* Notes */}
        <div>
          <label className="label">Notes (optional)</label>
          <textarea
            {...register('notes')}
            className="input min-h-[80px]"
            placeholder="Add any notes..."
            disabled={!canEditForm}
          />
        </div>

        {/* Submit */}
        <button
          type="submit"
          disabled={!canEditForm || createPTOMutation.isPending}
          className="btn-primary w-full py-3 text-lg"
        >
          {createPTOMutation.isPending ? 'Saving...' : 'Save PTO Entry'}
        </button>
      </form>
    </div>
  )
}
