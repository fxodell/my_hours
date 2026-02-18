import { Outlet, NavLink } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import OfflineIndicator from './OfflineIndicator'

function NavIcon({ icon, label }: { icon: React.ReactNode; label: string }) {
  return (
    <div className="flex flex-col items-center gap-1">
      {icon}
      <span className="text-xs">{label}</span>
    </div>
  )
}

export default function Layout() {
  const { user } = useAuth()

  const navLinkClass = ({ isActive }: { isActive: boolean }) =>
    `flex-1 flex justify-center py-2 ${
      isActive ? 'text-primary-600' : 'text-gray-500'
    }`

  return (
    <div className="page-container">
      <OfflineIndicator />
      {/* Header */}
      <header className="sticky top-0 bg-white border-b border-gray-200 z-10">
        <div className="px-4 py-3 flex items-center justify-between">
          <h1 className="text-lg font-semibold text-gray-900">MyHours</h1>
          <span className="text-sm text-gray-500">{user?.first_name}</span>
        </div>
      </header>

      {/* Main Content */}
      <main className="px-4 py-4">
        <Outlet />
      </main>

      {/* Bottom Navigation */}
      <nav className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 bottom-nav z-10">
        <div className="flex items-center justify-around">
          <NavLink to="/" className={navLinkClass} end>
            <NavIcon
              icon={
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
                </svg>
              }
              label="Home"
            />
          </NavLink>

          <NavLink to="/entry" className={navLinkClass}>
            <NavIcon
              icon={
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                </svg>
              }
              label="Add Time"
            />
          </NavLink>

          <NavLink to="/timesheets" className={navLinkClass}>
            <NavIcon
              icon={
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
              }
              label="Timesheets"
            />
          </NavLink>

          {(user?.is_manager || user?.is_admin) && (
            <NavLink to="/approvals" className={navLinkClass}>
              <NavIcon
                icon={
                  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                }
                label="Approve"
              />
            </NavLink>
          )}

          <NavLink to="/profile" className={navLinkClass}>
            <NavIcon
              icon={
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
              }
              label="Profile"
            />
          </NavLink>
        </div>
      </nav>
    </div>
  )
}
