import { useState, useEffect, useRef } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import * as api from '../services/api'
import type { TimeEntryCreate } from '../types'
import SearchableSelect from '../components/SearchableSelect'
import { getEntryDateMax, isTimesheetEditable, isTimesheetReadOnly } from '../timesheetStatus'
import { googleMapsDirectionsUrl, parseCoord } from '../utils/maps'

const HOUR_OPTIONS = [
  0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5, 5.5, 6, 6.5, 7, 7.5, 8,
  8.5, 9, 9.5, 10, 10.5, 11, 11.5, 12
]

const VEHICLE_TIERS = [
  { value: '', label: 'None' },
  { value: '<3 Hours $30', label: '<3 Hours - $30' },
  { value: '3-5 Hours $60', label: '3-5 Hours - $60' },
  { value: '5.5-6 Hours $90', label: '5.5-6 Hours - $90' },
  { value: '>6 Hours $120', label: '>6 Hours - $120' },
]

interface FormData {
  work_date: string
  client_id: string
  location_id: string
  job_code_id: string
  service_type_id: string
  work_mode: 'remote' | 'on_site'
  hours: number
  start_time: string
  end_time: string
  description: string
  vehicle_reimbursement_tier: string
}

type DurationInputMode = 'by_times' | 'by_hours'

function calcHoursFromTimes(start: string, end: string): number | null {
  if (!start || !end) return null
  const [sh, sm] = start.split(':').map(Number)
  const [eh, em] = end.split(':').map(Number)
  const diff = (eh * 60 + em - (sh * 60 + sm)) / 60
  if (diff <= 0) return null
  return Math.round(diff * 4) / 4
}

export default function TimeEntryEdit() {
  const { timesheetId, entryId } = useParams<{ timesheetId: string; entryId: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [error, setError] = useState('')
  const [durationInputMode, setDurationInputMode] = useState<DurationInputMode>('by_hours')

  const { data: timesheet } = useQuery({
    queryKey: ['timesheet', timesheetId],
    queryFn: () => api.getTimesheet(timesheetId!),
    enabled: !!timesheetId,
  })

  const { data: entries } = useQuery({
    queryKey: ['timeEntries', timesheetId],
    queryFn: () => api.getTimeEntries(timesheetId!),
    enabled: !!timesheetId,
  })

  const { data: payPeriod } = useQuery({
    queryKey: ['payPeriod', timesheet?.pay_period_id],
    queryFn: () => api.getPayPeriod(timesheet!.pay_period_id),
    enabled: !!timesheet?.pay_period_id,
  })

  const entry = entries?.find(e => e.id === entryId)

  const { data: clients } = useQuery({
    queryKey: ['clients'],
    queryFn: () => api.getClients(),
  })

  const { data: serviceTypes } = useQuery({
    queryKey: ['serviceTypes'],
    queryFn: () => api.getServiceTypes(),
  })

  const { register, handleSubmit, watch, reset, setValue, formState: { errors } } = useForm<FormData>({
    defaultValues: {
      work_date: '',
      work_mode: 'remote',
      hours: 8,
      start_time: '',
      end_time: '',
      description: '',
      vehicle_reimbursement_tier: '',
      client_id: '',
      location_id: '',
      job_code_id: '',
      service_type_id: '',
    },
  })

  // Load entry data into form when available
  useEffect(() => {
    if (entry) {
      const hasTimes = !!(entry.start_time && entry.end_time)
      setDurationInputMode(hasTimes ? 'by_times' : 'by_hours')
      reset({
        work_date: entry.work_date,
        work_mode: entry.work_mode,
        hours: Number(entry.hours),
        start_time: entry.start_time || '',
        end_time: entry.end_time || '',
        description: entry.description || '',
        vehicle_reimbursement_tier: entry.vehicle_reimbursement_tier || '',
        client_id: entry.client_id || '',
        location_id: entry.location_id || '',
        job_code_id: entry.job_code_id || '',
        service_type_id: entry.service_type_id || '',
      })
    }
  }, [entry, reset])

  const workMode = watch('work_mode')
  const startTime = watch('start_time')
  const endTime = watch('end_time')
  const hoursWatched = watch('hours')
  const selectedClientId = watch('client_id')
  const selectedLocationId = watch('location_id')

  // Auto-calculate hours from start/end only in time-range mode
  useEffect(() => {
    if (durationInputMode !== 'by_times') return
    const calculated = calcHoursFromTimes(startTime, endTime)
    if (calculated !== null) {
      setValue('hours', calculated)
    }
  }, [startTime, endTime, setValue, durationInputMode])

  // Track whether entry data has loaded to avoid resetting on initial populate
  const entryLoadedRef = useRef(false)
  useEffect(() => {
    if (entry) entryLoadedRef.current = true
  }, [entry])

  // Fetch locations when client changes (staleTime: 0 so approved location requests appear immediately)
  const { data: locations } = useQuery({
    queryKey: ['locations', selectedClientId],
    queryFn: () => api.getLocations(selectedClientId),
    enabled: !!selectedClientId,
    staleTime: 0,
  })

  // Fetch job codes when location changes (staleTime: 0 so approved job codes appear immediately)
  const { data: jobCodes } = useQuery({
    queryKey: ['jobCodes', selectedLocationId],
    queryFn: () => api.getJobCodes(selectedLocationId),
    enabled: !!selectedLocationId,
    staleTime: 0,
  })

  const selectedLocationDetail = locations?.find((l) => l.id === selectedLocationId)

  // Reset location and job code when client changes (skip initial entry load)
  const prevClientRef = useRef(selectedClientId)
  useEffect(() => {
    if (entryLoadedRef.current && prevClientRef.current !== selectedClientId) {
      setValue('location_id', '')
      setValue('job_code_id', '')
    }
    prevClientRef.current = selectedClientId
  }, [selectedClientId, setValue])

  // Reset job code when location changes (skip initial entry load)
  const prevLocationRef = useRef(selectedLocationId)
  useEffect(() => {
    if (entryLoadedRef.current && prevLocationRef.current !== selectedLocationId) {
      setValue('job_code_id', '')
    }
    prevLocationRef.current = selectedLocationId
  }, [selectedLocationId, setValue])

  const updateEntryMutation = useMutation({
    mutationFn: (data: Partial<TimeEntryCreate>) =>
      api.updateTimeEntry(timesheetId!, entryId!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['timeEntries', timesheetId] })
      queryClient.invalidateQueries({ queryKey: ['timesheet', timesheetId] })
      queryClient.invalidateQueries({ queryKey: ['currentTimesheet'] })
      navigate(`/timesheets/${timesheetId}`)
    },
    onError: (err) => {
      setError(err instanceof Error ? err.message : 'Failed to update entry')
    },
  })

  const onSubmit = (data: FormData) => {
    if (durationInputMode === 'by_times') {
      const calc = calcHoursFromTimes(data.start_time, data.end_time)
      if (!data.start_time?.trim() || !data.end_time?.trim() || calc === null) {
        setError('Enter a valid start and end time (end must be after start).')
        return
      }
      setError('')
    } else {
      setError('')
    }

    const updateData: Partial<TimeEntryCreate> = {
      work_date: data.work_date,
      client_id: data.client_id || undefined,
      location_id: data.location_id || undefined,
      job_code_id: data.job_code_id || undefined,
      service_type_id: data.service_type_id || undefined,
      work_mode: data.work_mode,
      hours: data.hours,
      start_time: durationInputMode === 'by_times' ? (data.start_time || undefined) : null,
      end_time: durationInputMode === 'by_times' ? (data.end_time || undefined) : null,
      description: data.description || undefined,
      vehicle_reimbursement_tier: data.vehicle_reimbursement_tier || undefined,
    }

    updateEntryMutation.mutate(updateData)
  }

  const canEdit = isTimesheetEditable(timesheet?.status)
  const maxWorkDate = getEntryDateMax(payPeriod?.end_date)

  if (!entry) {
    return (
      <div className="flex justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-gray-900">Edit Time Entry</h2>
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
            {...register('work_date', { required: 'Date is required' })}
            className="input"
            disabled={!canEdit}
            min={payPeriod?.start_date}
            max={maxWorkDate}
          />
          {payPeriod && (
            <p className="text-gray-500 text-xs mt-1">
              Valid dates: {payPeriod.start_date} to {maxWorkDate ?? payPeriod.end_date}
            </p>
          )}
          {errors.work_date && (
            <p className="text-red-500 text-sm mt-1">{errors.work_date.message}</p>
          )}
        </div>

        {/* Duration: start/end OR hours — mutually exclusive */}
        <div>
          <label className="label">Duration</label>
          <p className="text-gray-500 text-xs mb-2">Choose one: clock times (hours computed) or hours worked.</p>
          <div className="grid grid-cols-2 gap-2 mb-3">
            <label
              className={`flex items-center justify-center p-3 rounded-lg border cursor-pointer transition-colors text-sm text-center ${
                durationInputMode === 'by_times'
                  ? 'bg-primary-100 border-primary-500 text-primary-700'
                  : 'border-gray-300 hover:border-gray-400'
              } ${!canEdit ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              <input
                type="radio"
                name="duration_input_mode"
                checked={durationInputMode === 'by_times'}
                onChange={() => {
                  if (!canEdit) return
                  setDurationInputMode('by_times')
                }}
                className="sr-only"
                disabled={!canEdit}
              />
              Start &amp; end time
            </label>
            <label
              className={`flex items-center justify-center p-3 rounded-lg border cursor-pointer transition-colors text-sm text-center ${
                durationInputMode === 'by_hours'
                  ? 'bg-primary-100 border-primary-500 text-primary-700'
                  : 'border-gray-300 hover:border-gray-400'
              } ${!canEdit ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              <input
                type="radio"
                name="duration_input_mode"
                checked={durationInputMode === 'by_hours'}
                onChange={() => {
                  if (!canEdit) return
                  setDurationInputMode('by_hours')
                  setValue('start_time', '')
                  setValue('end_time', '')
                }}
                className="sr-only"
                disabled={!canEdit}
              />
              Hours worked
            </label>
          </div>

          {durationInputMode === 'by_times' && (
            <>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-xs font-medium text-gray-700">Start</label>
                  <input
                    type="time"
                    {...register('start_time')}
                    className="input"
                    disabled={!canEdit}
                  />
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-700">End</label>
                  <input
                    type="time"
                    {...register('end_time')}
                    className="input"
                    disabled={!canEdit}
                  />
                </div>
              </div>
              {startTime && endTime && calcHoursFromTimes(startTime, endTime) !== null && (
                <p className="text-gray-500 text-xs mt-1">
                  Hours worked: {calcHoursFromTimes(startTime, endTime)}h
                </p>
              )}
              {startTime && endTime && calcHoursFromTimes(startTime, endTime) === null && (
                <p className="text-red-500 text-xs mt-1">End time must be after start time</p>
              )}
            </>
          )}

          {durationInputMode === 'by_hours' && (
            <div className="grid grid-cols-4 gap-2">
              {HOUR_OPTIONS.map((h) => (
                <button
                  key={h}
                  type="button"
                  disabled={!canEdit}
                  onClick={() => setValue('hours', h, { shouldDirty: true, shouldTouch: true })}
                  className={`flex items-center justify-center p-3 rounded-lg border transition-colors text-sm ${
                    Number(hoursWatched) === h
                      ? 'bg-primary-100 border-primary-500 text-primary-700'
                      : 'border-gray-300 hover:border-gray-400'
                  } ${!canEdit ? 'opacity-50 cursor-not-allowed' : ''}`}
                >
                  {h}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Work Mode */}
        <div>
          <label className="label">Work Mode</label>
          <div className="grid grid-cols-2 gap-2">
            <label
              className={`flex items-center justify-center p-3 rounded-lg border cursor-pointer transition-colors ${
                workMode === 'remote'
                  ? 'bg-primary-100 border-primary-500 text-primary-700'
                  : 'border-gray-300 hover:border-gray-400'
              } ${!canEdit ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              <input
                type="radio"
                value="remote"
                {...register('work_mode')}
                className="sr-only"
                disabled={!canEdit}
              />
              <svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
              </svg>
              Remote
            </label>
            <label
              className={`flex items-center justify-center p-3 rounded-lg border cursor-pointer transition-colors ${
                workMode === 'on_site'
                  ? 'bg-primary-100 border-primary-500 text-primary-700'
                  : 'border-gray-300 hover:border-gray-400'
              } ${!canEdit ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              <input
                type="radio"
                value="on_site"
                {...register('work_mode')}
                className="sr-only"
                disabled={!canEdit}
              />
              <svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
              </svg>
              On-Site
            </label>
          </div>
        </div>

        {/* Client */}
        <div>
          <label className="label">Client</label>
          <select
            {...register('client_id')}
            className="input"
            disabled={!canEdit}
          >
            <option value="">Select a client</option>
            {clients?.map((client) => (
              <option key={client.id} value={client.id}>
                {client.name}
              </option>
            ))}
          </select>
        </div>

        {/* Location */}
        {selectedClientId && locations && locations.length > 0 && (
          <div>
            <label className="label">Location</label>
            <SearchableSelect
              options={(locations || []).map((l) => ({
                value: l.id,
                label: `${l.site_code ? `[${l.site_code}] ` : ''}${l.region ? `${l.region} - ` : ''}${l.site_name}`,
              }))}
              value={watch('location_id')}
              onChange={(val) => setValue('location_id', val)}
              placeholder="Select a location"
              disabled={!canEdit}
            />
            {selectedLocationDetail && (
              <div className="mt-2 text-sm space-y-1 rounded-lg border border-gray-100 bg-gray-50 px-3 py-2">
                {selectedLocationDetail.site_code && (
                  <p>
                    <span className="text-gray-500">Site code:</span>{' '}
                    <span className="font-mono">{selectedLocationDetail.site_code}</span>
                  </p>
                )}
                {selectedLocationDetail.job_codes && selectedLocationDetail.job_codes.length > 0 && (
                  <p>
                    <span className="text-gray-500">Job codes:</span>{' '}
                    <span className="font-mono">
                      {selectedLocationDetail.job_codes.map((j) => j.code).join(', ')}
                    </span>
                  </p>
                )}
                {(() => {
                  const lat = parseCoord(selectedLocationDetail.latitude)
                  const lng = parseCoord(selectedLocationDetail.longitude)
                  const url =
                    lat !== null && lng !== null ? googleMapsDirectionsUrl(lat, lng) : null
                  if (!url) {
                    return (
                      <p className="text-xs text-gray-400">No GPS on file for this location.</p>
                    )
                  }
                  return (
                    <a
                      href={url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-primary-600 font-medium"
                    >
                      Directions in Google Maps
                    </a>
                  )
                })()}
              </div>
            )}
          </div>
        )}

        {/* Job Code */}
        {selectedLocationId && (
          <div>
            <label className="label">Job Code</label>
            {jobCodes && jobCodes.length > 0 ? (
              <select
                {...register('job_code_id')}
                className="input"
                disabled={!canEdit}
              >
                <option value="">Select a job code</option>
                {jobCodes.map((jobCode) => (
                  <option key={jobCode.id} value={jobCode.id}>
                    {jobCode.code}{jobCode.description ? ` - ${jobCode.description}` : ''}
                  </option>
                ))}
              </select>
            ) : (
              <p className="text-sm text-gray-500 py-2">No job codes for this location.</p>
            )}
          </div>
        )}

        {/* Service Type */}
        <div>
          <label className="label">Service Type</label>
          <select
            {...register('service_type_id')}
            className="input"
            disabled={!canEdit}
          >
            <option value="">Select a service type</option>
            {serviceTypes?.map((st) => (
              <option key={st.id} value={st.id}>
                {st.name}
              </option>
            ))}
          </select>
        </div>

        {/* Description */}
        <div>
          <label className="label">Description of Work</label>
          <textarea
            {...register('description')}
            className="input min-h-[100px]"
            placeholder="Describe the work performed..."
            disabled={!canEdit}
          />
        </div>

        {/* Vehicle Reimbursement */}
        {workMode === 'on_site' && (
          <div>
            <label className="label">Personal Vehicle Reimbursement</label>
            <select
              {...register('vehicle_reimbursement_tier')}
              className="input"
              disabled={!canEdit}
            >
              {VEHICLE_TIERS.map((tier) => (
                <option key={tier.value} value={tier.value}>
                  {tier.label}
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Submit */}
        <button
          type="submit"
          disabled={!canEdit || updateEntryMutation.isPending}
          className="btn-primary w-full py-3 text-lg"
        >
          {updateEntryMutation.isPending ? 'Saving...' : 'Save Changes'}
        </button>
      </form>
    </div>
  )
}
