import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { format, parseISO } from 'date-fns'
import * as api from '../services/api'
import { useAuth } from '../contexts/AuthContext'
import type { User } from '../types'

interface EmployeeFormData {
  email: string
  password: string
  first_name: string
  last_name: string
  hire_date: string
  pay_period_group: string
  hourly_rate?: number
  is_manager: boolean
  is_admin: boolean
}

export default function Employees() {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [editingEmployee, setEditingEmployee] = useState<User | null>(null)
  const [formData, setFormData] = useState<EmployeeFormData>({
    email: '',
    password: '',
    first_name: '',
    last_name: '',
    hire_date: format(new Date(), 'yyyy-MM-dd'),
    pay_period_group: 'A',
    hourly_rate: undefined,
    is_manager: false,
    is_admin: false,
  })
  const [error, setError] = useState('')

  const { data: employees, isLoading } = useQuery({
    queryKey: ['employees'],
    queryFn: api.getEmployees,
  })

  const createMutation = useMutation({
    mutationFn: (data: EmployeeFormData) => api.createEmployee(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['employees'] })
      resetForm()
    },
    onError: (err) => {
      setError(err instanceof Error ? err.message : 'Failed to create employee')
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<EmployeeFormData> }) =>
      api.updateEmployee(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['employees'] })
      resetForm()
    },
    onError: (err) => {
      setError(err instanceof Error ? err.message : 'Failed to update employee')
    },
  })

  const resetForm = () => {
    setShowForm(false)
    setEditingEmployee(null)
    setFormData({
      email: '',
      password: '',
      first_name: '',
      last_name: '',
      hire_date: format(new Date(), 'yyyy-MM-dd'),
      pay_period_group: 'A',
      hourly_rate: undefined,
      is_manager: false,
      is_admin: false,
    })
    setError('')
  }

  const handleEdit = (employee: User) => {
    setEditingEmployee(employee)
    setFormData({
      email: employee.email,
      password: '',
      first_name: employee.first_name,
      last_name: employee.last_name,
      hire_date: employee.hire_date,
      pay_period_group: employee.pay_period_group,
      hourly_rate: undefined,
      is_manager: employee.is_manager,
      is_admin: employee.is_admin,
    })
    setShowForm(true)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    if (editingEmployee) {
      const updateData: Partial<EmployeeFormData> = {
        email: formData.email,
        first_name: formData.first_name,
        last_name: formData.last_name,
        pay_period_group: formData.pay_period_group,
        is_manager: formData.is_manager,
        is_admin: formData.is_admin,
      }
      updateMutation.mutate({ id: editingEmployee.id, data: updateData })
    } else {
      createMutation.mutate(formData)
    }
  }

  const toggleActive = (employee: User) => {
    updateMutation.mutate({
      id: employee.id,
      data: { is_active: !employee.is_active },
    })
  }

  if (!user?.is_admin) {
    return (
      <div className="text-center py-12 text-gray-500">
        <p>You do not have permission to manage employees.</p>
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
        <h2 className="text-xl font-bold text-gray-900">Employee Management</h2>
        {!showForm && (
          <button
            onClick={() => setShowForm(true)}
            className="btn-primary"
          >
            Add Employee
          </button>
        )}
      </div>

      {/* Add/Edit Form */}
      {showForm && (
        <div className="card p-4">
          <h3 className="font-semibold text-gray-900 mb-4">
            {editingEmployee ? 'Edit Employee' : 'Add New Employee'}
          </h3>

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm mb-4">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="label">First Name</label>
                <input
                  type="text"
                  value={formData.first_name}
                  onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                  className="input"
                  required
                />
              </div>
              <div>
                <label className="label">Last Name</label>
                <input
                  type="text"
                  value={formData.last_name}
                  onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                  className="input"
                  required
                />
              </div>
            </div>

            <div>
              <label className="label">Email</label>
              <input
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                className="input"
                required
              />
            </div>

            {!editingEmployee && (
              <div>
                <label className="label">Password</label>
                <input
                  type="password"
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  className="input"
                  required={!editingEmployee}
                  minLength={6}
                />
              </div>
            )}

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="label">Hire Date</label>
                <input
                  type="date"
                  value={formData.hire_date}
                  onChange={(e) => setFormData({ ...formData, hire_date: e.target.value })}
                  className="input"
                  required
                />
              </div>
              <div>
                <label className="label">Pay Period Group</label>
                <select
                  value={formData.pay_period_group}
                  onChange={(e) => setFormData({ ...formData, pay_period_group: e.target.value })}
                  className="input"
                  required
                >
                  <option value="A">Group A</option>
                  <option value="B">Group B</option>
                </select>
              </div>
            </div>

            <div className="flex items-center gap-6">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={formData.is_manager}
                  onChange={(e) => setFormData({ ...formData, is_manager: e.target.checked })}
                  className="w-4 h-4 rounded border-gray-300 text-primary-600"
                />
                <span className="text-gray-700">Manager</span>
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={formData.is_admin}
                  onChange={(e) => setFormData({ ...formData, is_admin: e.target.checked })}
                  className="w-4 h-4 rounded border-gray-300 text-primary-600"
                />
                <span className="text-gray-700">Admin</span>
              </label>
            </div>

            <div className="flex gap-2">
              <button
                type="button"
                onClick={resetForm}
                className="btn-secondary flex-1"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={createMutation.isPending || updateMutation.isPending}
                className="btn-primary flex-1"
              >
                {createMutation.isPending || updateMutation.isPending
                  ? 'Saving...'
                  : editingEmployee
                  ? 'Update Employee'
                  : 'Add Employee'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Employee List */}
      <div className="space-y-3">
        {employees?.map((employee) => (
          <div
            key={employee.id}
            className={`card p-4 ${!employee.is_active ? 'opacity-60' : ''}`}
          >
            <div className="flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <p className="font-medium text-gray-900">{employee.full_name}</p>
                  {employee.is_admin && (
                    <span className="px-2 py-0.5 text-xs font-medium bg-purple-100 text-purple-800 rounded-full">
                      Admin
                    </span>
                  )}
                  {employee.is_manager && !employee.is_admin && (
                    <span className="px-2 py-0.5 text-xs font-medium bg-blue-100 text-blue-800 rounded-full">
                      Manager
                    </span>
                  )}
                  {!employee.is_active && (
                    <span className="px-2 py-0.5 text-xs font-medium bg-gray-100 text-gray-800 rounded-full">
                      Inactive
                    </span>
                  )}
                </div>
                <p className="text-sm text-gray-500">{employee.email}</p>
                <p className="text-xs text-gray-400 mt-1">
                  Group {employee.pay_period_group} | Hired{' '}
                  {format(parseISO(employee.hire_date), 'MMM d, yyyy')}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleEdit(employee)}
                  className="p-2 text-gray-500 hover:text-primary-600 hover:bg-gray-100 rounded-lg"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                  </svg>
                </button>
                <button
                  onClick={() => toggleActive(employee)}
                  className={`p-2 rounded-lg ${
                    employee.is_active
                      ? 'text-gray-500 hover:text-red-600 hover:bg-gray-100'
                      : 'text-gray-500 hover:text-green-600 hover:bg-gray-100'
                  }`}
                >
                  {employee.is_active ? (
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
                    </svg>
                  ) : (
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  )}
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
