import { NavLink } from 'react-router-dom'

const links = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/team', label: 'Team Builder' },
  { to: '/live', label: 'Live Race' },
  { to: '/standings', label: 'Standings' },
  { to: '/chips', label: 'Chip Advisor' },
  { to: '/title-race', label: 'Title Race' },
  { to: '/validation', label: 'Score Check' },
]

export default function Navbar() {
  return (
    <>
      {/* Mobile: brand-only top bar — navigation is via BottomNav */}
      <div className="sm:hidden bg-gray-900 border-b border-gray-800 px-4 h-12 flex items-center justify-between">
        <span className="text-red-500 font-bold text-base tracking-tight">F1 Points Engine</span>
        <NavLink
          to="/help"
          className={({ isActive }) =>
            `p-1.5 rounded transition-colors ${isActive ? 'text-red-400' : 'text-gray-400 hover:text-white'}`
          }
          aria-label="Help"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="w-5 h-5">
            <circle cx="12" cy="12" r="10" />
            <path strokeLinecap="round" strokeLinejoin="round" d="M9.09 9a3 3 0 015.83 1c0 2-3 3-3 3" />
            <line x1="12" y1="17" x2="12.01" y2="17" strokeLinecap="round" />
          </svg>
        </NavLink>
      </div>

      {/* Desktop: full navbar with links */}
      <nav className="hidden sm:block bg-gray-900 border-b-2 border-red-600">
        <div className="container mx-auto px-4 flex items-center gap-6 h-14">
          <span className="text-red-500 font-bold text-lg tracking-tight">F1 Points Engine</span>
          <div className="flex gap-1 overflow-x-auto flex-1">
            {links.map((l) => (
              <NavLink
                key={l.to}
                to={l.to}
                className={({ isActive }) =>
                  `px-3 py-1.5 rounded text-sm font-medium whitespace-nowrap transition-colors ${
                    isActive
                      ? 'bg-red-600 text-white'
                      : 'text-gray-400 hover:text-white hover:bg-gray-800'
                  }`
                }
              >
                {l.label}
              </NavLink>
            ))}
          </div>
          <NavLink
            to="/help"
            className={({ isActive }) =>
              `p-1.5 rounded transition-colors ${isActive ? 'text-red-400' : 'text-gray-400 hover:text-white'}`
            }
            aria-label="Help"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="w-5 h-5">
              <circle cx="12" cy="12" r="10" />
              <path strokeLinecap="round" strokeLinejoin="round" d="M9.09 9a3 3 0 015.83 1c0 2-3 3-3 3" />
              <line x1="12" y1="17" x2="12.01" y2="17" strokeLinecap="round" />
            </svg>
          </NavLink>
        </div>
      </nav>
    </>
  )
}
