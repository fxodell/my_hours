import { Outlet, NavLink } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import OfflineIndicator from './OfflineIndicator'

function NavIcon({ icon, label }: { icon: React.ReactNode; label: string }) {
  return (
    <div className="flex flex-col items-center gap-0.5">
      {icon}
      <span className="text-[10px] leading-tight">{label}</span>
    </div>
  )
}

export default function Layout() {
  const { user } = useAuth()
  const isManager = user?.is_manager || user?.is_admin

  const navLinkClass = ({ isActive }: { isActive: boolean }) =>
    `flex-1 flex justify-center py-1.5 ${
      isActive ? 'text-primary-600' : 'text-gray-500'
    }`

  return (
    <div className="page-container">
      <OfflineIndicator />
      {/* Header */}
      <header className="fixed top-0 left-0 right-0 bg-white border-b border-gray-200 z-10">
        <div className="px-4 py-3 flex items-center justify-between">
          <h1 className="text-lg font-semibold text-gray-900">MyHours</h1>
          <span className="text-sm text-gray-500">{user?.first_name}</span>
        </div>
      </header>

      {/* Main Content — pt-14 compensates for fixed header */}
      <main className="px-4 py-4 pt-14">
        <Outlet />
      </main>

      {/* Bottom Navigation — two compact rows */}
      <nav className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 bottom-nav z-10">
        {/* Row 1: Primary actions */}
        <div className="flex items-center justify-around">
          <NavLink to="/" className={navLinkClass} end>
            <NavIcon
              icon={
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
                </svg>
              }
              label="Home"
            />
          </NavLink>

          <NavLink to="/entry" className={navLinkClass}>
            <NavIcon
              icon={
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                </svg>
              }
              label="Add Time"
            />
          </NavLink>

          <NavLink to="/timesheets" className={navLinkClass}>
            <NavIcon
              icon={
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
              }
              label="Timesheets"
            />
          </NavLink>
        </div>

        {/* Row 2: Secondary actions */}
        <div className="flex items-center justify-around border-t border-gray-100">
          <NavLink to="/location-lookup" className={navLinkClass}>
            <NavIcon
              icon={
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
                </svg>
              }
              label="Map"
            />
          </NavLink>

          <NavLink to="/site-requests" className={navLinkClass}>
            <NavIcon
              icon={
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
              }
              label="Loc. reqs"
            />
          </NavLink>

          {isManager && (
            <NavLink to="/approvals" className={navLinkClass}>
              <NavIcon
                icon={
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                }
                label="Approve"
              />
            </NavLink>
          )}

          <NavLink to="/reports" className={navLinkClass}>
            <NavIcon
              icon={
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              }
              label="Reports"
            />
          </NavLink>

          <NavLink to="/profile" className={navLinkClass}>
            <NavIcon
              icon={
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
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
