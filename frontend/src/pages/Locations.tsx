import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import * as api from '../services/api'
import { useAuth } from '../contexts/AuthContext'
import type { Client, Location, JobCode } from '../types'

interface LocationFormData {
  site_name: string
  region: string
  is_active: boolean
}

interface JobCodeFormData {
  code: string
  description: string
}

export default function Locations() {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [selectedClientId, setSelectedClientId] = useState<string>('')
  const [showForm, setShowForm] = useState(false)
  const [editingLocation, setEditingLocation] = useState<Location | null>(null)
  const [expandedLocation, setExpandedLocation] = useState<string | null>(null)
  const [showJobCodeForm, setShowJobCodeForm] = useState<string | null>(null)
  const [formData, setFormData] = useState<LocationFormData>({
    site_name: '',
    region: '',
    is_active: true,
  })
  const [jobCodeData, setJobCodeData] = useState<JobCodeFormData>({
    code: '',
    description: '',
  })
  const [error, setError] = useState('')

  const { data: clients } = useQuery({
    queryKey: ['clients', 'all'],
    queryFn: api.getAllClients,
  })

  const { data: locations, isLoading } = useQuery({
    queryKey: ['locations', 'admin', selectedClientId],
    queryFn: () => api.getAllLocations(selectedClientId || undefined),
    enabled: !!selectedClientId,
  })

  const createMutation = useMutation({
    mutationFn: (data: LocationFormData) =>
      api.createLocation({
        client_id: selectedClientId,
        site_name: data.site_name,
        region: data.region || undefined,
        is_active: data.is_active,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['locations'] })
      resetForm()
    },
    onError: (err) => {
      setError(err instanceof Error ? err.message : 'Failed to create location')
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<LocationFormData> }) =>
      api.updateLocation(id, { ...data, region: data.region || null }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['locations'] })
      resetForm()
    },
    onError: (err) => {
      setError(err instanceof Error ? err.message : 'Failed to update location')
    },
  })

  const createJobCodeMutation = useMutation({
    mutationFn: ({ locationId, data }: { locationId: string; data: JobCodeFormData }) =>
      api.createJobCode(locationId, {
        code: data.code,
        description: data.description || undefined,
      }),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['jobCodes', variables.locationId] })
      setShowJobCodeForm(null)
      setJobCodeData({ code: '', description: '' })
    },
    onError: (err) => {
      setError(err instanceof Error ? err.message : 'Failed to create job code')
    },
  })

  const resetForm = () => {
    setShowForm(false)
    setEditingLocation(null)
    setFormData({ site_name: '', region: '', is_active: true })
    setError('')
  }

  const handleEdit = (loc: Location) => {
    setEditingLocation(loc)
    setFormData({
      site_name: loc.site_name,
      region: loc.region || '',
      is_active: loc.is_active,
    })
    setShowForm(true)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (editingLocation) {
      updateMutation.mutate({ id: editingLocation.id, data: formData })
    } else {
      createMutation.mutate(formData)
    }
  }

  const handleJobCodeSubmit = (e: React.FormEvent, locationId: string) => {
    e.preventDefault()
    createJobCodeMutation.mutate({ locationId, data: jobCodeData })
  }

  if (!user?.is_admin) {
    return (
      <div className="text-center py-12 text-gray-500">
        <p>You do not have permission to manage locations.</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-gray-900">Locations</h2>
        {selectedClientId && !showForm && (
          <button onClick={() => setShowForm(true)} className="btn-primary">
            Add Location
          </button>
        )}
      </div>

      {/* Client Selector */}
      <div>
        <label className="label">Select Client</label>
        <select
          value={selectedClientId}
          onChange={(e) => {
            setSelectedClientId(e.target.value)
            resetForm()
            setExpandedLocation(null)
          }}
          className="input"
        >
          <option value="">-- Select a client --</option>
          {clients?.map((c: Client) => (
            <option key={c.id} value={c.id}>
              {c.name} {!c.is_active ? '(Inactive)' : ''}
            </option>
          ))}
        </select>
      </div>

      {!selectedClientId && (
        <p className="text-center py-8 text-gray-500">Select a client to manage its locations.</p>
      )}

      {/* Create/Edit Location Form */}
      {showForm && selectedClientId && (
        <div className="card p-4">
          <h3 className="font-semibold text-gray-900 mb-4">
            {editingLocation ? 'Edit Location' : 'Add New Location'}
          </h3>

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm mb-4">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="label">Site Name</label>
              <input
                type="text"
                value={formData.site_name}
                onChange={(e) => setFormData({ ...formData, site_name: e.target.value })}
                className="input"
                required
              />
            </div>

            <div>
              <label className="label">Region</label>
              <input
                type="text"
                value={formData.region}
                onChange={(e) => setFormData({ ...formData, region: e.target.value })}
                className="input"
                placeholder="e.g. South Texas, Permian Basin"
              />
            </div>

            {editingLocation && (
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={formData.is_active}
                  onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                  className="w-4 h-4 rounded border-gray-300 text-primary-600"
                />
                <span className="text-gray-700">Active</span>
              </label>
            )}

            <div className="flex gap-2">
              <button type="button" onClick={resetForm} className="btn-secondary flex-1">
                Cancel
              </button>
              <button
                type="submit"
                disabled={createMutation.isPending || updateMutation.isPending}
                className="btn-primary flex-1"
              >
                {createMutation.isPending || updateMutation.isPending
                  ? 'Saving...'
                  : editingLocation
                  ? 'Update Location'
                  : 'Add Location'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Location List */}
      {selectedClientId && (
        <div className="space-y-3">
          {isLoading ? (
            <div className="flex justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
            </div>
          ) : locations?.length === 0 ? (
            <p className="text-center py-8 text-gray-500">
              No locations for this client. Add one to get started.
            </p>
          ) : (
            locations?.map((loc) => (
              <div
                key={loc.id}
                className={`card ${!loc.is_active ? 'opacity-60' : ''}`}
              >
                <div className="p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex-1" onClick={() => setExpandedLocation(expandedLocation === loc.id ? null : loc.id)}>
                      <div className="flex items-center gap-2 cursor-pointer">
                        <svg
                          className={`w-4 h-4 text-gray-400 transition-transform ${
                            expandedLocation === loc.id ? 'rotate-90' : ''
                          }`}
                          fill="none"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                        >
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                        </svg>
                        <p className="font-medium text-gray-900">{loc.site_name}</p>
                        {!loc.is_active && (
                          <span className="px-2 py-0.5 text-xs font-medium bg-gray-100 text-gray-800 rounded-full">
                            Inactive
                          </span>
                        )}
                      </div>
                      {loc.region && (
                        <p className="text-sm text-gray-500 ml-8">{loc.region}</p>
                      )}
                    </div>
                    <button
                      onClick={() => handleEdit(loc)}
                      className="p-2 text-gray-500 hover:text-primary-600 hover:bg-gray-100 rounded-lg"
                    >
                      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                      </svg>
                    </button>
                  </div>
                </div>

                {/* Expanded Job Codes */}
                {expandedLocation === loc.id && (
                  <JobCodeSection
                    locationId={loc.id}
                    showForm={showJobCodeForm === loc.id}
                    onToggleForm={() => {
                      setShowJobCodeForm(showJobCodeForm === loc.id ? null : loc.id)
                      setJobCodeData({ code: '', description: '' })
                    }}
                    formData={jobCodeData}
                    onFormDataChange={setJobCodeData}
                    onSubmit={(e) => handleJobCodeSubmit(e, loc.id)}
                    isPending={createJobCodeMutation.isPending}
                    error={error}
                  />
                )}
              </div>
            ))
          )}
        </div>
      )}
    </div>
  )
}

function JobCodeSection({
  locationId,
  showForm,
  onToggleForm,
  formData,
  onFormDataChange,
  onSubmit,
  isPending,
  error,
}: {
  locationId: string
  showForm: boolean
  onToggleForm: () => void
  formData: JobCodeFormData
  onFormDataChange: (data: JobCodeFormData) => void
  onSubmit: (e: React.FormEvent) => void
  isPending: boolean
  error: string
}) {
  const { data: jobCodes, isLoading } = useQuery({
    queryKey: ['jobCodes', locationId],
    queryFn: () => api.getJobCodes(locationId),
  })

  return (
    <div className="border-t border-gray-200 px-4 py-3 bg-gray-50">
      <div className="flex items-center justify-between mb-2">
        <p className="text-sm font-medium text-gray-700">Job Codes</p>
        {!showForm && (
          <button
            onClick={onToggleForm}
            className="text-xs text-primary-600 hover:text-primary-800 font-medium"
          >
            + Add Job Code
          </button>
        )}
      </div>

      {showForm && (
        <form onSubmit={onSubmit} className="mb-3 p-3 bg-white rounded-lg border border-gray-200">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-3 py-2 rounded text-xs mb-2">
              {error}
            </div>
          )}
          <div className="grid grid-cols-2 gap-2 mb-2">
            <div>
              <label className="text-xs text-gray-600">Code</label>
              <input
                type="text"
                value={formData.code}
                onChange={(e) => onFormDataChange({ ...formData, code: e.target.value })}
                className="input text-sm"
                required
                placeholder="e.g. JC-001"
              />
            </div>
            <div>
              <label className="text-xs text-gray-600">Description</label>
              <input
                type="text"
                value={formData.description}
                onChange={(e) => onFormDataChange({ ...formData, description: e.target.value })}
                className="input text-sm"
                placeholder="Optional"
              />
            </div>
          </div>
          <div className="flex gap-2">
            <button type="button" onClick={onToggleForm} className="btn-secondary text-xs py-1 flex-1">
              Cancel
            </button>
            <button type="submit" disabled={isPending} className="btn-primary text-xs py-1 flex-1">
              {isPending ? 'Adding...' : 'Add'}
            </button>
          </div>
        </form>
      )}

      {isLoading ? (
        <p className="text-xs text-gray-400">Loading...</p>
      ) : jobCodes?.length === 0 ? (
        <p className="text-xs text-gray-400">No job codes yet.</p>
      ) : (
        <div className="space-y-1">
          {jobCodes?.map((jc: JobCode) => (
            <div
              key={jc.id}
              className={`flex items-center justify-between text-sm py-1 ${
                !jc.is_active ? 'opacity-50' : ''
              }`}
            >
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs bg-gray-200 px-1.5 py-0.5 rounded">{jc.code}</span>
                {jc.description && (
                  <span className="text-gray-600">{jc.description}</span>
                )}
              </div>
              {!jc.is_active && (
                <span className="text-xs text-gray-400">Inactive</span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
