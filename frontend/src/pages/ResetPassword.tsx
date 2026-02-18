import { useState } from 'react'
import { Link, useSearchParams, useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import * as api from '../services/api'

export default function ResetPassword() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const token = searchParams.get('token') || ''

  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)

  const resetMutation = useMutation({
    mutationFn: () => api.resetPassword(token, password),
    onSuccess: () => {
      setSuccess(true)
      setError('')
    },
    onError: (err) => {
      setError(err instanceof Error ? err.message : 'Reset failed')
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (!token) {
      setError('Invalid reset link. Please request a new one.')
      return
    }

    if (password.length < 6) {
      setError('Password must be at least 6 characters')
      return
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match')
      return
    }

    resetMutation.mutate()
  }

  if (!token) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
        <div className="max-w-md w-full space-y-6">
          <div className="text-center">
            <h1 className="text-3xl font-bold text-primary-600">MyHours</h1>
            <h2 className="mt-4 text-xl font-semibold text-gray-900">Invalid Reset Link</h2>
          </div>

          <div className="card p-6 text-center">
            <p className="text-gray-600">
              This password reset link is invalid or has expired.
            </p>
          </div>

          <div className="text-center">
            <Link to="/forgot-password" className="text-primary-600 hover:text-primary-700 font-medium">
              Request a new reset link
            </Link>
          </div>
        </div>
      </div>
    )
  }

  if (success) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
        <div className="max-w-md w-full space-y-6">
          <div className="text-center">
            <h1 className="text-3xl font-bold text-primary-600">MyHours</h1>
            <h2 className="mt-4 text-xl font-semibold text-gray-900">Password Reset</h2>
          </div>

          <div className="card p-6 text-center">
            <div className="w-16 h-16 mx-auto mb-4 bg-green-100 rounded-full flex items-center justify-center">
              <svg className="w-8 h-8 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <p className="text-gray-600 mb-4">
              Your password has been reset successfully.
            </p>
            <button
              onClick={() => navigate('/login')}
              className="btn-primary"
            >
              Sign In
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="max-w-md w-full space-y-6">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-primary-600">MyHours</h1>
          <h2 className="mt-4 text-xl font-semibold text-gray-900">Reset Your Password</h2>
          <p className="mt-2 text-gray-600">
            Enter your new password below.
          </p>
        </div>

        <div className="card p-6">
          {error && (
            <div className="mb-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="password" className="label">
                New Password
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="input"
                placeholder="Enter new password"
                required
                minLength={6}
              />
            </div>

            <div>
              <label htmlFor="confirmPassword" className="label">
                Confirm Password
              </label>
              <input
                id="confirmPassword"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="input"
                placeholder="Confirm new password"
                required
              />
            </div>

            <button
              type="submit"
              disabled={resetMutation.isPending}
              className="btn-primary w-full"
            >
              {resetMutation.isPending ? 'Resetting...' : 'Reset Password'}
            </button>
          </form>
        </div>

        <div className="text-center">
          <Link to="/login" className="text-primary-600 hover:text-primary-700 font-medium">
            Back to Sign In
          </Link>
        </div>
      </div>
    </div>
  )
}
