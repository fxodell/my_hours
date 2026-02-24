import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
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

export default function PTOEntryEdit() {
  const navigate = useNavigate()
  const { timesheetId, entryId } = useParams<{ timesheetId: string; entryId: string }>()
  const queryClient = useQueryClient()
  const [error, setError] = useState('')

  const { data: timesheet } = useQuery({
    queryKey: ['timesheet', timesheetId],
    queryFn: () => api.getTimesheet(timesheetId!),
    enabled: !!timesheetId,
  })

  const { data: payPeriod } = useQuery({
    queryKey: ['payPeriod', timesheet?.pay_period_id],
    queryFn: () => api.getPayPeriod(timesheet!.pay_period_id),
    enabled: !!timesheet?.pay_period_id,
  })

  const { data: ptoEntries } = useQuery({
    queryKey: ['ptoEntries', timesheetId],
    queryFn: () => api.getPTOEntries(timesheetId!),
    enabled: !!timesheetId,
  })

  const entry = ptoEntries?.find((e) => e.id === entryId)

  const { register, handleSubmit, watch, reset, formState: { errors } } = useForm<FormData>({
    defaultValues: {
      pto_date: '',
      pto_type: 'personal',
      hours: 8,
      notes: '',
    },
  })

  // Load entry data when available
  useEffect(() => {
    if (entry) {
      reset({
        pto_date: entry.pto_date,
        pto_type: entry.pto_type as FormData['pto_type'],
        hours: Number(entry.hours),
        notes: entry.notes || '',
      })
    }
  }, [entry, reset])

  const updatePTOMutation = useMutation({
    mutationFn: (data: FormData) =>
      api.updatePTOEntry(timesheetId!, entryId!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ptoEntries', timesheetId] })
      queryClient.invalidateQueries({ queryKey: ['timesheet', timesheetId] })
      navigate(`/timesheets/${timesheetId}`)
    },
    onError: (err) => {
      setError(err instanceof Error ? err.message : 'Failed to update PTO entry')
    },
  })

  const onSubmit = (data: FormData) => {
    if (!timesheet) return
    updatePTOMutation.mutate(data)
  }

  const canEdit = isTimesheetEditable(timesheet?.status)
  const maxPTODate = getEntryDateMax(payPeriod?.end_date)

  if (!entry && ptoEntries) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">PTO entry not found</p>
        <button onClick={() => navigate(-1)} className="btn-secondary mt-4">
          Go Back
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-gray-900">Edit PTO</h2>
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

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        {/* Date */}
        <div>
          <label className="label">Date</label>
          <input
            type="date"
            {...register('pto_date', { required: 'Date is required' })}
            className="input"
            disabled={!canEdit}
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
                } ${!canEdit ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                <input
                  type="radio"
                  value={type.value}
                  {...register('pto_type')}
                  className="sr-only"
                  disabled={!canEdit}
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
                } ${!canEdit ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                <input
                  type="radio"
                  value={h}
                  {...register('hours', { valueAsNumber: true })}
                  className="sr-only"
                  disabled={!canEdit}
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
            disabled={!canEdit}
          />
        </div>

        {/* Submit */}
        <button
          type="submit"
          disabled={!canEdit || updatePTOMutation.isPending}
          className="btn-primary w-full py-3 text-lg"
        >
          {updatePTOMutation.isPending ? 'Saving...' : 'Update PTO Entry'}
        </button>
      </form>
    </div>
  )
}
