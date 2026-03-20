import { useState, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { format, parseISO, differenceInCalendarDays } from 'date-fns'
import * as api from '../services/api'
import type { TimeEntryCreate, SiteRequestCreate } from '../types'
import SearchableSelect from '../components/SearchableSelect'
import { getEntryDateMax, isTimesheetEditable, isTimesheetReadOnly } from '../timesheetStatus'

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

function calcHoursFromTimes(start: string, end: string): number | null {
  if (!start || !end) return null
  const [sh, sm] = start.split(':').map(Number)
  const [eh, em] = end.split(':').map(Number)
  const diff = (eh * 60 + em - (sh * 60 + sm)) / 60
  if (diff <= 0) return null
  return Math.round(diff * 4) / 4 // round to nearest 0.25
}

function SiteRequestInlineForm({
  clientId,
  isPending,
  onSubmit,
  onCancel,
}: {
  clientId: string
  isPending: boolean
  onSubmit: (data: SiteRequestCreate) => void
  onCancel: () => void
}) {
  const [siteName, setSiteName] = useState('')
  const [region, setRegion] = useState('')
  const [jobCode, setJobCode] = useState('')
  const [notes, setNotes] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (!siteName.trim()) return
    onSubmit({
      client_id: clientId,
      site_name: siteName.trim(),
      region: region.trim() || undefined,
      job_code: jobCode.trim() || undefined,
      notes: notes.trim() || undefined,
    })
  }

  return (
    <div className="space-y-2">
      <div>
        <label className="text-xs font-medium text-gray-700">Site Name *</label>
        <input
          type="text"
          value={siteName}
          onChange={(e) => setSiteName(e.target.value)}
          className="input text-sm"
          placeholder="e.g. Well Pad A-14"
          required
        />
      </div>
      <div>
        <label className="text-xs font-medium text-gray-700">Region</label>
        <input
          type="text"
          value={region}
          onChange={(e) => setRegion(e.target.value)}
          className="input text-sm"
          placeholder="e.g. Alpine High"
        />
      </div>
      <div>
        <label className="text-xs font-medium text-gray-700">AFE / Job Code</label>
        <input
          type="text"
          value={jobCode}
          onChange={(e) => setJobCode(e.target.value)}
          className="input text-sm"
          placeholder="e.g. AFE-12345"
        />
      </div>
      <div>
        <label className="text-xs font-medium text-gray-700">Notes</label>
        <input
          type="text"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          className="input text-sm"
          placeholder="e.g. new well starting next week"
        />
      </div>
      <div className="flex gap-2">
        <button
          type="button"
          onClick={handleSubmit}
          disabled={!siteName.trim() || isPending}
          className="btn btn-primary text-sm flex-1"
        >
          {isPending ? 'Submitting...' : 'Submit Request'}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="btn btn-secondary text-sm"
        >
          Cancel
        </button>
      </div>
    </div>
  )
}

export default function TimeEntry() {
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

  // Filter to only current periods (containing today)
  const today = format(new Date(), 'yyyy-MM-dd')
  const currentPeriods = recentPeriods?.filter(
    (pp) => pp.start_date <= today && pp.end_date >= today
  )

  // Auto-select the current period
  useEffect(() => {
    if (currentPeriods && currentPeriods.length > 0 && !selectedPeriodId) {
      setSelectedPeriodId(currentPeriods[0].id)
    }
  }, [currentPeriods, selectedPeriodId])

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

  const { data: clients } = useQuery({
    queryKey: ['clients'],
    queryFn: api.getClients,
  })

  const { data: serviceTypes } = useQuery({
    queryKey: ['serviceTypes'],
    queryFn: api.getServiceTypes,
  })

  const { register, handleSubmit, watch, setValue, formState: { errors } } = useForm<FormData>({
    defaultValues: {
      work_date: format(new Date(), 'yyyy-MM-dd'),
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

  const workMode = watch('work_mode')
  const startTime = watch('start_time')
  const endTime = watch('end_time')
  const selectedClientId = watch('client_id')
  const selectedLocationId = watch('location_id')

  // Auto-calculate hours from start/end times
  useEffect(() => {
    const calculated = calcHoursFromTimes(startTime, endTime)
    if (calculated !== null) {
      setValue('hours', calculated)
    }
  }, [startTime, endTime, setValue])

  // Fetch locations when client changes
  const { data: locations } = useQuery({
    queryKey: ['locations', selectedClientId],
    queryFn: () => api.getLocations(selectedClientId),
    enabled: !!selectedClientId,
  })

  // Fetch job codes when location changes
  const { data: jobCodes } = useQuery({
    queryKey: ['jobCodes', selectedLocationId],
    queryFn: () => api.getJobCodes(selectedLocationId),
    enabled: !!selectedLocationId,
  })

  // Reset location when client changes
  useEffect(() => {
    setValue('location_id', '')
    setValue('job_code_id', '')
  }, [selectedClientId, setValue])

  // Reset job code when location changes
  useEffect(() => {
    setValue('job_code_id', '')
  }, [selectedLocationId, setValue])

  const createEntryMutation = useMutation({
    mutationFn: (data: TimeEntryCreate) =>
      api.createTimeEntry(timesheet!.id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['timeEntries', timesheet!.id] })
      queryClient.invalidateQueries({ queryKey: ['timesheet', timesheet!.id] })
      queryClient.invalidateQueries({ queryKey: ['currentTimesheet'] })
      navigate('/')
    },
    onError: (err) => {
      setError(err instanceof Error ? err.message : 'Failed to create entry')
    },
  })

  const onSubmit = (data: FormData) => {
    if (!timesheet) return

    const entry: TimeEntryCreate = {
      work_date: data.work_date,
      client_id: data.client_id || undefined,
      location_id: data.location_id || undefined,
      job_code_id: data.job_code_id || undefined,
      service_type_id: data.service_type_id || undefined,
      work_mode: data.work_mode,
      hours: data.hours,
      start_time: data.start_time || undefined,
      end_time: data.end_time || undefined,
      description: data.description || undefined,
      vehicle_reimbursement_tier: data.vehicle_reimbursement_tier || undefined,
      is_billable: true,
    }

    createEntryMutation.mutate(entry)
  }

  const [showSiteRequest, setShowSiteRequest] = useState(false)
  const [siteRequestSent, setSiteRequestSent] = useState(false)

  const siteRequestMutation = useMutation({
    mutationFn: api.createSiteRequest,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['siteRequests'] })
      setShowSiteRequest(false)
      setSiteRequestSent(true)
    },
  })

  // Reset site request state when client changes
  useEffect(() => {
    setShowSiteRequest(false)
    setSiteRequestSent(false)
  }, [selectedClientId])

  const canEdit = isTimesheetEditable(timesheet?.status)
  const maxWorkDate = getEntryDateMax(payPeriod?.end_date)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-gray-900">Add Time Entry</h2>
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
        {/* Pay Period Selector */}
        {!timesheetParam && currentPeriods && currentPeriods.length > 1 && (
          <div>
            <label className="label">Pay Period</label>
            <div className="grid grid-cols-1 gap-2">
              {currentPeriods
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

        {/* Start / End Time */}
        <div>
          <label className="label">Start &amp; End Time (optional)</label>
          <div className="grid grid-cols-2 gap-2">
            <input
              type="time"
              {...register('start_time')}
              className="input"
              disabled={!canEdit}
              placeholder="Start"
            />
            <input
              type="time"
              {...register('end_time')}
              className="input"
              disabled={!canEdit}
              placeholder="End"
            />
          </div>
          {startTime && endTime && calcHoursFromTimes(startTime, endTime) !== null && (
            <p className="text-gray-500 text-xs mt-1">
              Calculated: {calcHoursFromTimes(startTime, endTime)}h
            </p>
          )}
          {startTime && endTime && calcHoursFromTimes(startTime, endTime) === null && (
            <p className="text-red-500 text-xs mt-1">
              End time must be after start time
            </p>
          )}
        </div>

        {/* Hours - Large buttons for easy mobile selection */}
        <div>
          <label className="label">Hours Worked</label>
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

        {/* Location - Show when client is selected */}
        {selectedClientId && (
          <div>
            <label className="label">Location</label>
            {locations && locations.length > 0 ? (
              <SearchableSelect
                options={(locations || []).map((l) => ({
                  value: l.id,
                  label: `${l.region ? `${l.region} - ` : ''}${l.site_name}`,
                }))}
                value={watch('location_id')}
                onChange={(val) => setValue('location_id', val)}
                placeholder="Select a location"
                disabled={!canEdit}
              />
            ) : (
              <p className="text-sm text-gray-500 py-2">No locations for this client yet.</p>
            )}

            {/* Site request success message */}
            {siteRequestSent && (
              <div className="bg-green-50 border border-green-200 text-green-700 px-3 py-2 rounded-lg text-sm mt-2 flex items-center gap-2">
                <svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                Site request submitted. Your manager will review it shortly.
              </div>
            )}

            {/* Request new site toggle */}
            {!showSiteRequest && !siteRequestSent && (
              <button
                type="button"
                onClick={() => setShowSiteRequest(true)}
                className="text-sm text-primary-600 mt-1 flex items-center gap-1"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                </svg>
                Can't find your site? Request a new one
              </button>
            )}

            {/* Inline site request form */}
            {showSiteRequest && (
              <div className="mt-2 border border-primary-200 bg-primary-50 rounded-lg p-3 space-y-3">
                <div className="flex items-center justify-between">
                  <h4 className="font-medium text-sm text-gray-900">Request New Site</h4>
                  <button
                    type="button"
                    onClick={() => setShowSiteRequest(false)}
                    className="text-gray-400 hover:text-gray-600"
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>

                {siteRequestMutation.isError && (
                  <p className="text-red-600 text-sm">{(siteRequestMutation.error as Error).message}</p>
                )}

                <SiteRequestInlineForm
                  clientId={selectedClientId}
                  isPending={siteRequestMutation.isPending}
                  onSubmit={(data) => siteRequestMutation.mutate(data)}
                  onCancel={() => setShowSiteRequest(false)}
                />
              </div>
            )}
          </div>
        )}

        {/* Job Code - Only show when location is selected */}
        {selectedLocationId && jobCodes && jobCodes.length > 0 && (
          <div>
            <label className="label">Job Code</label>
            <select
              {...register('job_code_id')}
              className="input"
              disabled={!canEdit}
            >
              <option value="">Select a job code</option>
              {jobCodes?.map((jobCode) => (
                <option key={jobCode.id} value={jobCode.id}>
                  {jobCode.code}{jobCode.description ? ` - ${jobCode.description}` : ''}
                </option>
              ))}
            </select>
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
          disabled={!canEdit || createEntryMutation.isPending}
          className="btn-primary w-full py-3 text-lg"
        >
          {createEntryMutation.isPending ? 'Saving...' : 'Save Entry'}
        </button>
      </form>
    </div>
  )
}
