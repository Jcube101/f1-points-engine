import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchDrivers, fetchConstructors } from '../lib/api'
import { useTeam } from '../hooks/useTeam'
import { useOptimizer } from '../hooks/useOptimizer'
import DriverCard from '../components/DriverCard'
import ConstructorCard from '../components/ConstructorCard'
import TeamSummary from '../components/TeamSummary'
import type { Driver, Constructor, AssetResult } from '../lib/types'

type OptimizeMode = 'max_points' | 'best_value'

const BUDGET = 100_000_000

export default function TeamBuilder() {
  const [search, setSearch] = useState('')
  const [optimizeMode, setOptimizeMode] = useState<OptimizeMode>('max_points')
  const [activeTab, setActiveTab] = useState<'drivers' | 'constructors'>('drivers')

  const { data: drivers = [] } = useQuery({ queryKey: ['drivers'], queryFn: fetchDrivers })
  const { data: constructors = [] } = useQuery({ queryKey: ['constructors'], queryFn: fetchConstructors })

  const team = useTeam()
  const { loading, result, error, runOptimizer } = useOptimizer()

  const filteredDrivers = drivers.filter((d) =>
    d.name.toLowerCase().includes(search.toLowerCase()) ||
    d.team_name.toLowerCase().includes(search.toLowerCase())
  )

  const filteredConstructors = constructors.filter((c) =>
    c.name.toLowerCase().includes(search.toLowerCase())
  )

  function handleLoadOptimized() {
    if (!result) return
    const optimized = result[optimizeMode]
    const selectedDrivers = optimized.drivers
      .map((a: AssetResult) => drivers.find((d) => d.id === a.id))
      .filter(Boolean) as Driver[]
    const selectedConstructors = optimized.constructors
      .map((a: AssetResult) => constructors.find((c) => c.id === a.id))
      .filter(Boolean) as Constructor[]
    team.loadOptimized(selectedDrivers, selectedConstructors)
  }

  // Budget calculation for sticky footer
  const spent = team.drivers.reduce((s, d) => s + d.price, 0) +
    team.constructors.reduce((s, c) => s + c.price, 0)
  const remaining = BUDGET - spent
  const budgetPct = Math.min(100, (spent / BUDGET) * 100)

  return (
    <div className="space-y-4 pb-44 sm:pb-0">
      {/* Header — desktop shows optimize button here */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Team Builder</h1>
        {/* Desktop-only optimize controls in header */}
        <div className="hidden sm:flex gap-2">
          <button
            onClick={() => runOptimizer()}
            disabled={loading}
            className="min-h-[44px] px-4 py-2 bg-red-600 hover:bg-red-500 text-white text-sm font-medium rounded-lg disabled:opacity-50 transition-colors"
          >
            {loading ? 'Optimising...' : 'Optimise'}
          </button>
          {result && (
            <button
              onClick={handleLoadOptimized}
              className="min-h-[44px] px-4 py-2 bg-green-700 hover:bg-green-600 text-white text-sm font-medium rounded-lg transition-colors"
            >
              Load Team
            </button>
          )}
        </div>
      </div>

      {error && <div className="text-red-400 text-sm bg-red-950/30 rounded p-3">{error}</div>}

      {/* Optimizer result (both mobile + desktop) */}
      {result && (
        <div className="bg-gray-800 rounded-lg p-3 border border-gray-700 text-sm">
          <div className="flex items-center gap-3 mb-2 flex-wrap">
            {(['max_points', 'best_value'] as OptimizeMode[]).map((mode) => (
              <button
                key={mode}
                onClick={() => setOptimizeMode(mode)}
                className={`min-h-[36px] px-3 py-1 rounded font-medium transition-colors ${
                  optimizeMode === mode ? 'bg-red-600 text-white' : 'text-gray-400 hover:text-white'
                }`}
              >
                {mode === 'max_points' ? 'Max Points' : 'Best Value'}
              </button>
            ))}
            {/* Mobile-only Load Team button */}
            <button
              onClick={handleLoadOptimized}
              className="sm:hidden min-h-[36px] px-3 py-1 rounded bg-green-700 text-white text-xs font-medium"
            >
              Load Team
            </button>
          </div>
          <div className="text-gray-400 text-xs">
            Team xP: <span className="text-blue-400">{result[optimizeMode].total_xp.toFixed(1)}</span>
            {' · '}
            Cost: <span className="text-green-400">${(result[optimizeMode].total_price / 1e6).toFixed(1)}M</span>
            {' · '}
            {result[optimizeMode].feasible ? (
              <span className="text-green-400">Valid</span>
            ) : (
              <span className="text-red-400">No feasible solution</span>
            )}
          </div>
        </div>
      )}

      <div className="grid lg:grid-cols-3 gap-4">
        {/* Asset picker */}
        <div className="lg:col-span-2 space-y-3">
          <input
            type="text"
            placeholder="Search drivers or teams..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-red-500"
          />

          {/* Tab toggle — full-width tap targets on mobile */}
          <div className="flex gap-2">
            {(['drivers', 'constructors'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`flex-1 sm:flex-none min-h-[44px] px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  activeTab === tab ? 'bg-gray-700 text-white' : 'text-gray-400 hover:text-white bg-gray-800/50'
                }`}
              >
                {tab.charAt(0).toUpperCase() + tab.slice(1)}
              </button>
            ))}
          </div>

          {/* Cards — single column on mobile, 2 col on sm+ */}
          {activeTab === 'drivers' ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {filteredDrivers.map((d) => (
                <DriverCard
                  key={d.id}
                  driver={d}
                  selected={!!team.drivers.find((x) => x.id === d.id)}
                  onSelect={(drv) => {
                    if (team.drivers.find((x) => x.id === drv.id)) {
                      team.removeDriver(drv.id)
                    } else {
                      team.addDriver(drv)
                    }
                  }}
                />
              ))}
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {filteredConstructors.map((c) => (
                <ConstructorCard
                  key={c.id}
                  constructor={c}
                  selected={!!team.constructors.find((x) => x.id === c.id)}
                  onSelect={(con) => {
                    if (team.constructors.find((x) => x.id === con.id)) {
                      team.removeConstructor(con.id)
                    } else {
                      team.addConstructor(con)
                    }
                  }}
                />
              ))}
            </div>
          )}
        </div>

        {/* Desktop sidebar: TeamSummary */}
        <div className="space-y-3">
          <TeamSummary
            drivers={team.drivers}
            constructors={team.constructors}
            drsBoostDriverId={team.drsBoostDriverId}
            onRemoveDriver={team.removeDriver}
            onRemoveConstructor={team.removeConstructor}
            onSetDrs={team.setDrsBoost}
          />

          <div className="bg-gray-800 rounded-lg p-3 border border-gray-700">
            <label className="flex items-center gap-2 text-sm cursor-pointer min-h-[44px]">
              <input
                type="checkbox"
                checked={team.noNegative}
                onChange={(e) => team.setNoNegative(e.target.checked)}
                className="rounded w-4 h-4"
              />
              <span className="text-gray-300">No Negative chip</span>
            </label>
          </div>

          {(team.drivers.length > 0 || team.constructors.length > 0) && (
            <button
              onClick={team.clearTeam}
              className="w-full py-2 text-sm text-gray-400 hover:text-red-400 transition-colors"
            >
              Clear team
            </button>
          )}
        </div>
      </div>

      {/* ── Mobile sticky footer: DRS pills + budget + optimize ──────────────── */}
      {/* Positioned above the 56px BottomNav (bottom-14 = 3.5rem = 56px) */}
      <div className="sm:hidden fixed bottom-14 left-0 right-0 z-40 bg-gray-900 border-t border-gray-700 px-4 pt-2 pb-2 shadow-lg">
        {/* DRS boost pills — horizontally scrollable */}
        {team.drivers.length > 0 && (
          <div className="mb-2">
            <p className="text-xs text-gray-500 mb-1">DRS Boost — tap to select:</p>
            <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-none">
              {team.drivers.map((d) => (
                <button
                  key={d.id}
                  onClick={() => team.setDrsBoost(d.id)}
                  className={`flex-shrink-0 min-h-[36px] px-3 py-1 rounded-full text-xs font-bold border transition-colors ${
                    team.drsBoostDriverId === d.id
                      ? 'border-yellow-500 bg-yellow-500/20 text-yellow-300'
                      : 'border-gray-600 bg-gray-800 text-gray-300'
                  }`}
                >
                  {team.drsBoostDriverId === d.id ? '⚡ ' : ''}{d.code}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Budget bar */}
        <div className="flex justify-between text-xs text-gray-400 mb-1">
          <span>${(spent / 1e6).toFixed(1)}M used</span>
          <span className={remaining < 0 ? 'text-red-400 font-bold' : 'text-green-400'}>
            {remaining < 0 ? '-' : ''}${(Math.abs(remaining) / 1e6).toFixed(1)}M remaining
          </span>
        </div>
        <div className="w-full bg-gray-700 rounded-full h-1.5 mb-2">
          <div
            className={`h-1.5 rounded-full transition-all ${budgetPct >= 100 ? 'bg-red-500' : 'bg-green-500'}`}
            style={{ width: `${budgetPct}%` }}
          />
        </div>

        {/* Full-width Optimize button */}
        <button
          onClick={() => runOptimizer()}
          disabled={loading}
          className="w-full min-h-[48px] bg-red-600 hover:bg-red-500 text-white font-semibold rounded-lg text-sm disabled:opacity-50 transition-colors"
        >
          {loading ? 'Optimising...' : 'Optimise Team'}
        </button>
      </div>
    </div>
  )
}
