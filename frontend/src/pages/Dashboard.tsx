import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { fetchDrivers, fetchRaces, fetchLiveStatus } from '../lib/api'

export default function Dashboard() {
  const { data: drivers = [] } = useQuery({ queryKey: ['drivers'], queryFn: fetchDrivers })
  const { data: races = [] } = useQuery({ queryKey: ['races'], queryFn: () => fetchRaces(2026) })
  const { data: liveStatus } = useQuery({
    queryKey: ['liveStatus'],
    queryFn: fetchLiveStatus,
    refetchInterval: 30_000,
  })

  const topDrivers = [...drivers].sort((a, b) => b.xp - a.xp).slice(0, 5)
  const today = new Date()
  const allUpcoming = races.filter((r) => new Date(r.date) >= today)
  const nextRace = allUpcoming[0]
  const upcomingRaces = allUpcoming.slice(0, 3)
  const seasonStarted = races.some((r) => new Date(r.date) < today)
  const daysUntil = nextRace
    ? Math.max(0, Math.ceil((new Date(nextRace.date).getTime() - today.getTime()) / 86_400_000))
    : null

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Dashboard</h1>
        {liveStatus?.is_live && (
          <span className="flex items-center gap-2 text-red-400 text-sm font-medium">
            <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
            Live: {liveStatus.session_type}
          </span>
        )}
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label="Drivers" value={drivers.length} />
        <StatCard label="Races in Season" value={races.length} />
        <StatCard label="Races Remaining" value={allUpcoming.length} />
        <StatCard
          label={seasonStarted ? 'Next Race' : 'Season Starts'}
          value={
            nextRace
              ? `${nextRace.name.replace(' Grand Prix', ' GP')} — R${nextRace.round_number}`
              : 'Season over'
          }
          subtitle={daysUntil !== null ? `In ${daysUntil} day${daysUntil === 1 ? '' : 's'}` : undefined}
          small
        />
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Top xP Drivers */}
        <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
          <h2 className="font-bold text-white mb-3">Top Expected Points (xP)</h2>
          <div className="space-y-2">
            {topDrivers.map((d, i) => (
              <div key={d.id} className="flex items-center gap-3">
                <span className="text-gray-500 text-xs w-4">{i + 1}</span>
                <div className="flex-1 flex items-center gap-2">
                  <div className="w-1 h-5 rounded" style={{ backgroundColor: d.team_color }} />
                  <span className="text-sm text-white">{d.name}</span>
                </div>
                <div className="text-right">
                  <span className="text-sm font-bold text-blue-400">{d.xp.toFixed(1)}</span>
                  <span className="text-xs text-gray-500 ml-1">xP</span>
                </div>
                <div className="text-right w-16">
                  <span className="text-xs text-green-400">${(d.price / 1e6).toFixed(1)}M</span>
                </div>
              </div>
            ))}
          </div>
          <Link to="/team" className="mt-3 block text-center text-xs text-red-400 hover:text-red-300">
            Build your team →
          </Link>
        </div>

        {/* Upcoming Races */}
        <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
          <h2 className="font-bold text-white mb-3">Upcoming Races</h2>
          {upcomingRaces.length === 0 ? (
            <p className="text-gray-400 text-sm">Season complete</p>
          ) : (
            <div className="space-y-3">
              {upcomingRaces.map((r) => (
                <div key={r.id} className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-white">{r.name}</p>
                    <p className="text-xs text-gray-400">{r.circuit} · {r.circuit_type}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm text-gray-300">{new Date(r.date).toLocaleDateString()}</p>
                    <p className="text-xs text-gray-500">Round {r.round_number}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
          <Link to="/standings" className="mt-3 block text-center text-xs text-red-400 hover:text-red-300">
            View full standings →
          </Link>
        </div>
      </div>

      {/* Quick links */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        {[
          { to: '/team', title: 'Team Builder', desc: 'Pick your 5 drivers + 2 constructors and optimise' },
          { to: '/live', title: 'Live Race', desc: 'Real-time fantasy points during race weekends' },
          { to: '/chips', title: 'Chip Advisor', desc: 'Get a data-driven chip recommendation' },
        ].map((card) => (
          <Link
            key={card.to}
            to={card.to}
            className="bg-gray-800 rounded-lg p-4 border border-gray-700 hover:border-red-500 transition-colors group min-h-[72px]"
          >
            <h3 className="font-semibold text-white group-hover:text-red-400 transition-colors">
              {card.title}
            </h3>
            <p className="text-xs text-gray-400 mt-1">{card.desc}</p>
          </Link>
        ))}
      </div>
    </div>
  )
}

function StatCard({ label, value, small, subtitle }: { label: string; value: string | number; small?: boolean; subtitle?: string }) {
  return (
    <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
      <p className="text-xs text-gray-400">{label}</p>
      <p className={`font-bold text-white mt-1 ${small ? 'text-sm' : 'text-2xl'}`}>{value}</p>
      {subtitle && <p className="text-xs text-gray-500 mt-0.5">{subtitle}</p>}
    </div>
  )
}
