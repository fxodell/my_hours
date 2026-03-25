import { useForm } from 'react-hook-form'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import * as api from '../services/api'
import type { SiteRequestCreate } from '../types'

export default function SiteRequestForm() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<SiteRequestCreate>()

  const { data: clients } = useQuery({
    queryKey: ['clients'],
    queryFn: () => api.getClients(),
  })

  const mutation = useMutation({
    mutationFn: api.createSiteRequest,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['siteRequests'] })
      navigate('/site-requests')
    },
  })

  const onSubmit = (data: SiteRequestCreate) => {
    mutation.mutate({
      ...data,
      region: data.region?.trim() || undefined,
      job_code: data.job_code?.trim() || undefined,
      job_code_description: data.job_code_description?.trim() || undefined,
      notes: data.notes?.trim() || undefined,
    })
  }

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">Request New Location</h2>

      {mutation.isError && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {(mutation.error as Error).message}
        </div>
      )}

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div>
          <label className="label">Client *</label>
          <select
            {...register('client_id', { required: 'Client is required' })}
            className="input"
          >
            <option value="">Select a client</option>
            {clients?.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
          {errors.client_id && (
            <p className="text-red-500 text-sm mt-1">{errors.client_id.message}</p>
          )}
        </div>

        <div>
          <label className="label">Location name *</label>
          <input
            {...register('site_name', { required: 'Location name is required' })}
            className="input"
            placeholder="e.g. Well Pad A-14"
          />
          {errors.site_name && (
            <p className="text-red-500 text-sm mt-1">{errors.site_name.message}</p>
          )}
        </div>

        <div>
          <label className="label">Region</label>
          <input
            {...register('region')}
            className="input"
            placeholder="e.g. Alpine High"
          />
        </div>

        <div>
          <label className="label">AFE / Job Code</label>
          <input
            {...register('job_code')}
            className="input"
            placeholder="e.g. AFE-12345"
          />
        </div>

        <div>
          <label className="label">Job Code Description</label>
          <input
            {...register('job_code_description')}
            className="input"
            placeholder="e.g. Drilling operations"
          />
        </div>

        <div>
          <label className="label">Notes</label>
          <textarea
            {...register('notes')}
            className="input"
            rows={3}
            placeholder="Any additional details..."
          />
        </div>

        <div className="flex gap-3">
          <button
            type="submit"
            disabled={isSubmitting || mutation.isPending}
            className="btn btn-primary flex-1"
          >
            {mutation.isPending ? 'Submitting...' : 'Submit Request'}
          </button>
          <button
            type="button"
            onClick={() => navigate('/site-requests')}
            className="btn btn-secondary"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  )
}
