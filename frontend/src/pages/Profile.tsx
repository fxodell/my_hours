import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { useAuth } from '../contexts/AuthContext'
import { format, parseISO } from 'date-fns'
import * as api from '../services/api'

export default function Profile() {
  const { user, logout } = useAuth()
  const [showPasswordForm, setShowPasswordForm] = useState(false)
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const changePasswordMutation = useMutation({
    mutationFn: () => api.changePassword(currentPassword, newPassword),
    onSuccess: () => {
      setSuccess('Password changed successfully!')
      setShowPasswordForm(false)
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
      setError('')
    },
    onError: (err) => {
      setError(err instanceof Error ? err.message : 'Failed to change password')
    },
  })

  const handlePasswordSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (newPassword.length < 6) {
      setError('New password must be at least 6 characters')
      return
    }

    if (newPassword !== confirmPassword) {
      setError('Passwords do not match')
      return
    }

    changePasswordMutation.mutate()
  }

  if (!user) return null

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-gray-900">Profile</h2>

      {success && (
        <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg text-sm">
          {success}
        </div>
      )}

      <div className="card p-6">
        {/* Avatar */}
        <div className="flex flex-col items-center mb-6">
          <div className="w-20 h-20 rounded-full bg-primary-100 flex items-center justify-center text-primary-600 text-2xl font-bold">
            {user.first_name[0]}{user.last_name[0]}
          </div>
          <h3 className="mt-3 text-lg font-semibold text-gray-900">
            {user.full_name}
          </h3>
          <p className="text-gray-500">{user.email}</p>
        </div>

        {/* Details */}
        <div className="space-y-4">
          <div className="flex justify-between py-3 border-b border-gray-100">
            <span className="text-gray-500">Hire Date</span>
            <span className="text-gray-900 font-medium">
              {format(parseISO(user.hire_date), 'MMM d, yyyy')}
            </span>
          </div>

          <div className="flex justify-between py-3 border-b border-gray-100">
            <span className="text-gray-500">Pay Period Group</span>
            <span className="text-gray-900 font-medium">
              Group {user.pay_period_group}
            </span>
          </div>

          <div className="flex justify-between py-3 border-b border-gray-100">
            <span className="text-gray-500">Role</span>
            <span className="text-gray-900 font-medium">
              {user.is_admin ? 'Admin' : user.is_manager ? 'Manager' : 'Employee'}
            </span>
          </div>
        </div>
      </div>

      {/* Password Change */}
      <div className="card p-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-semibold text-gray-900">Password</h3>
            <p className="text-sm text-gray-500">Change your password</p>
          </div>
          {!showPasswordForm && (
            <button
              onClick={() => {
                setShowPasswordForm(true)
                setSuccess('')
              }}
              className="btn-secondary"
            >
              Change
            </button>
          )}
        </div>

        {showPasswordForm && (
          <form onSubmit={handlePasswordSubmit} className="mt-4 space-y-4">
            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
                {error}
              </div>
            )}

            <div>
              <label className="label">Current Password</label>
              <input
                type="password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                className="input"
                required
              />
            </div>

            <div>
              <label className="label">New Password</label>
              <input
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className="input"
                required
                minLength={6}
              />
            </div>

            <div>
              <label className="label">Confirm New Password</label>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="input"
                required
              />
            </div>

            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => {
                  setShowPasswordForm(false)
                  setCurrentPassword('')
                  setNewPassword('')
                  setConfirmPassword('')
                  setError('')
                }}
                className="btn-secondary flex-1"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={changePasswordMutation.isPending}
                className="btn-primary flex-1"
              >
                {changePasswordMutation.isPending ? 'Saving...' : 'Save'}
              </button>
            </div>
          </form>
        )}
      </div>

      {/* Actions */}
      <div className="space-y-3">
        <button
          onClick={logout}
          className="btn-danger w-full"
        >
          Sign Out
        </button>
      </div>

      {/* App Info */}
      <div className="text-center text-sm text-gray-400 pt-4">
        <p>MyHours v0.1.0</p>
      </div>
    </div>
  )
}
