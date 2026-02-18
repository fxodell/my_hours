import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import * as api from '../services/api'

export default function ForgotPassword() {
  const [email, setEmail] = useState('')
  const [submitted, setSubmitted] = useState(false)
  const [error, setError] = useState('')

  const resetMutation = useMutation({
    mutationFn: () => api.requestPasswordReset(email),
    onSuccess: () => {
      setSubmitted(true)
      setError('')
    },
    onError: (err) => {
      setError(err instanceof Error ? err.message : 'Request failed')
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!email) {
      setError('Please enter your email')
      return
    }
    resetMutation.mutate()
  }

  if (submitted) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
        <div className="max-w-md w-full space-y-6">
          <div className="text-center">
            <h1 className="text-3xl font-bold text-primary-600">MyHours</h1>
            <h2 className="mt-4 text-xl font-semibold text-gray-900">Check Your Email</h2>
          </div>

          <div className="card p-6 text-center">
            <div className="w-16 h-16 mx-auto mb-4 bg-green-100 rounded-full flex items-center justify-center">
              <svg className="w-8 h-8 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
            </div>
            <p className="text-gray-600">
              If an account exists for <strong>{email}</strong>, you will receive a password reset link.
            </p>
            <p className="text-sm text-gray-500 mt-4">
              (In development mode, check the server console for the reset token)
            </p>
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

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="max-w-md w-full space-y-6">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-primary-600">MyHours</h1>
          <h2 className="mt-4 text-xl font-semibold text-gray-900">Forgot Password</h2>
          <p className="mt-2 text-gray-600">
            Enter your email and we'll send you a reset link.
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
              <label htmlFor="email" className="label">
                Email address
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="input"
                placeholder="you@example.com"
                required
              />
            </div>

            <button
              type="submit"
              disabled={resetMutation.isPending}
              className="btn-primary w-full"
            >
              {resetMutation.isPending ? 'Sending...' : 'Send Reset Link'}
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
