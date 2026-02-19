import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import * as api from '../services/api'
import { useAuth } from '../contexts/AuthContext'
import type { Client } from '../types'

interface ClientFormData {
  name: string
  industry: string
  is_active: boolean
}

export default function Clients() {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [editingClient, setEditingClient] = useState<Client | null>(null)
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null)
  const [formData, setFormData] = useState<ClientFormData>({
    name: '',
    industry: '',
    is_active: true,
  })
  const [error, setError] = useState('')

  const { data: clients, isLoading } = useQuery({
    queryKey: ['clients', 'all'],
    queryFn: api.getAllClients,
  })

  const createMutation = useMutation({
    mutationFn: (data: ClientFormData) =>
      api.createClient({ name: data.name, industry: data.industry || undefined, is_active: data.is_active }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['clients'] })
      resetForm()
    },
    onError: (err) => {
      setError(err instanceof Error ? err.message : 'Failed to create client')
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<ClientFormData> }) =>
      api.updateClient(id, { ...data, industry: data.industry || null }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['clients'] })
      resetForm()
    },
    onError: (err) => {
      setError(err instanceof Error ? err.message : 'Failed to update client')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteClient(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['clients'] })
      setConfirmDelete(null)
    },
    onError: (err) => {
      setError(err instanceof Error ? err.message : 'Failed to delete client')
      setConfirmDelete(null)
    },
  })

  const resetForm = () => {
    setShowForm(false)
    setEditingClient(null)
    setFormData({ name: '', industry: '', is_active: true })
    setError('')
  }

  const handleEdit = (client: Client) => {
    setEditingClient(client)
    setFormData({
      name: client.name,
      industry: client.industry || '',
      is_active: client.is_active,
    })
    setShowForm(true)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (editingClient) {
      updateMutation.mutate({ id: editingClient.id, data: formData })
    } else {
      createMutation.mutate(formData)
    }
  }

  if (!user?.is_admin) {
    return (
      <div className="text-center py-12 text-gray-500">
        <p>You do not have permission to manage clients.</p>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-gray-900">Client Management</h2>
        {!showForm && (
          <button onClick={() => setShowForm(true)} className="btn-primary">
            Add Client
          </button>
        )}
      </div>

      {showForm && (
        <div className="card p-4">
          <h3 className="font-semibold text-gray-900 mb-4">
            {editingClient ? 'Edit Client' : 'Add New Client'}
          </h3>

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm mb-4">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="label">Name</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="input"
                required
              />
            </div>

            <div>
              <label className="label">Industry</label>
              <input
                type="text"
                value={formData.industry}
                onChange={(e) => setFormData({ ...formData, industry: e.target.value })}
                className="input"
                placeholder="e.g. Oil & Gas, Manufacturing"
              />
            </div>

            {editingClient && (
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
                  : editingClient
                  ? 'Update Client'
                  : 'Add Client'}
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="space-y-3">
        {clients?.map((client) => (
          <div
            key={client.id}
            className={`card p-4 ${!client.is_active ? 'opacity-60' : ''}`}
          >
            <div className="flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <p className="font-medium text-gray-900">{client.name}</p>
                  {!client.is_active && (
                    <span className="px-2 py-0.5 text-xs font-medium bg-gray-100 text-gray-800 rounded-full">
                      Inactive
                    </span>
                  )}
                </div>
                {client.industry && (
                  <p className="text-sm text-gray-500">{client.industry}</p>
                )}
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleEdit(client)}
                  className="p-2 text-gray-500 hover:text-primary-600 hover:bg-gray-100 rounded-lg"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                  </svg>
                </button>
                {confirmDelete === client.id ? (
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => deleteMutation.mutate(client.id)}
                      className="px-2 py-1 text-xs bg-red-600 text-white rounded"
                    >
                      Confirm
                    </button>
                    <button
                      onClick={() => setConfirmDelete(null)}
                      className="px-2 py-1 text-xs bg-gray-200 text-gray-700 rounded"
                    >
                      Cancel
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={() => setConfirmDelete(client.id)}
                    className="p-2 text-gray-500 hover:text-red-600 hover:bg-gray-100 rounded-lg"
                  >
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                )}
              </div>
            </div>
          </div>
        ))}
        {clients?.length === 0 && (
          <p className="text-center py-8 text-gray-500">No clients found. Add one to get started.</p>
        )}
      </div>
    </div>
  )
}
