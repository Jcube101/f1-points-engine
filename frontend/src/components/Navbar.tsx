import { NavLink } from 'react-router-dom'

const links = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/team', label: 'Team Builder' },
  { to: '/live', label: 'Live Race' },
  { to: '/standings', label: 'Standings' },
  { to: '/chips', label: 'Chip Advisor' },
  { to: '/validation', label: 'Score Check' },
]

export default function Navbar() {
  return (
    <nav className="bg-gray-900 border-b border-red-600 border-b-2">
      <div className="container mx-auto px-4 flex items-center gap-6 h-14">
        <span className="text-red-500 font-bold text-lg tracking-tight">F1 Points Engine</span>
        <div className="flex gap-1 overflow-x-auto">
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
      </div>
    </nav>
  )
}
