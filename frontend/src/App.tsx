import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './contexts/AuthContext'
import Layout from './components/Layout'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import TimeEntry from './pages/TimeEntry'
import TimeEntryEdit from './pages/TimeEntryEdit'
import PTOEntry from './pages/PTOEntry'
import PTOEntryEdit from './pages/PTOEntryEdit'
import Timesheets from './pages/Timesheets'
import TimesheetDetail from './pages/TimesheetDetail'
import Approvals from './pages/Approvals'
import Reports from './pages/Reports'
import Employees from './pages/Employees'
import Clients from './pages/Clients'
import ServiceTypes from './pages/ServiceTypes'
import LocationsPage from './pages/Locations'
import PayPeriodsPage from './pages/PayPeriods'
import Profile from './pages/Profile'
import ForgotPassword from './pages/ForgotPassword'
import ResetPassword from './pages/ResetPassword'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}

function ManagerRoute({ children }: { children: React.ReactNode }) {
  const { user } = useAuth()

  if (!user?.is_manager && !user?.is_admin) {
    return <Navigate to="/" replace />
  }

  return <>{children}</>
}

function AdminRoute({ children }: { children: React.ReactNode }) {
  const { user } = useAuth()

  if (!user?.is_admin) {
    return <Navigate to="/" replace />
  }

  return <>{children}</>
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="/reset-password" element={<ResetPassword />} />

      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="entry" element={<TimeEntry />} />
        <Route path="pto" element={<PTOEntry />} />
        <Route path="timesheets" element={<Timesheets />} />
        <Route path="timesheets/:id" element={<TimesheetDetail />} />
        <Route path="timesheets/:timesheetId/entries/:entryId/edit" element={<TimeEntryEdit />} />
        <Route path="timesheets/:timesheetId/pto/:entryId/edit" element={<PTOEntryEdit />} />
        <Route
          path="approvals"
          element={
            <ManagerRoute>
              <Approvals />
            </ManagerRoute>
          }
        />
        <Route
          path="reports"
          element={
            <ManagerRoute>
              <Reports />
            </ManagerRoute>
          }
        />
        <Route
          path="employees"
          element={
            <AdminRoute>
              <Employees />
            </AdminRoute>
          }
        />
        <Route
          path="clients"
          element={
            <AdminRoute>
              <Clients />
            </AdminRoute>
          }
        />
        <Route
          path="service-types"
          element={
            <AdminRoute>
              <ServiceTypes />
            </AdminRoute>
          }
        />
        <Route
          path="locations"
          element={
            <AdminRoute>
              <LocationsPage />
            </AdminRoute>
          }
        />
        <Route
          path="pay-periods"
          element={
            <AdminRoute>
              <PayPeriodsPage />
            </AdminRoute>
          }
        />
        <Route path="profile" element={<Profile />} />
      </Route>
    </Routes>
  )
}
