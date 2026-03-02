import { useState } from 'react'
import type { LiveSnapshot } from '../lib/types'

interface Props {
  snapshot: LiveSnapshot | null
  userDriverCodes?: string[]
}

export default function LiveTicker({ snapshot, userDriverCodes = [] }: Props) {
  const [expandedDriver, setExpandedDriver] = useState<string | null>(null)

  if (!snapshot) {
    return (
      <div className="bg-gray-800 rounded-lg p-8 text-center border border-gray-700">
        <p className="text-gray-400">No live session data</p>
        <p className="text-xs text-gray-600 mt-1">Live data appears during race weekends</p>
      </div>
    )
  }

  const lapProgress = snapshot.total_laps > 0 ? (snapshot.lap / snapshot.total_laps) * 100 : 0

  return (
    <div className="space-y-3">
      {/* Session progress bar — sticky at top of scroll area */}
      <div className="sticky top-0 z-20 bg-gray-900 pb-2">
        <div className="bg-gray-800 rounded-lg p-3 border border-gray-700">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold text-red-400 uppercase tracking-wide">
                {snapshot.session_type}
              </span>
              {snapshot.stale && (
                <span className="text-xs text-yellow-500 border border-yellow-700 px-1.5 py-0.5 rounded font-medium">
                  Stale
                </span>
              )}
            </div>
            <span className="text-xs text-gray-500">
              {new Date(snapshot.timestamp).toLocaleTimeString()}
            </span>
          </div>
          {snapshot.session_type === 'race' && (
            <div>
              <div className="flex justify-between text-xs text-gray-400 mb-1">
                <span className="font-medium">Lap {snapshot.lap}</span>
                <span>of {snapshot.total_laps}</span>
              </div>
              <div className="w-full bg-gray-700 rounded-full h-2">
                <div
                  className="h-2 rounded-full bg-red-500 transition-all"
                  style={{ width: `${lapProgress}%` }}
                />
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Driver table */}
      <div className="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
        <div className="divide-y divide-gray-700">
          {snapshot.drivers.map((d) => {
            const isUser = userDriverCodes.includes(d.driver_id)
            const isExpanded = expandedDriver === d.driver_id
            const pts = d.fantasy_points
            const ptsPositive = pts > 0
            const ptsNegative = pts < 0

            return (
              <div key={d.driver_id}>
                {/* ── Main row (tappable) ─────────────────────────── */}
                <button
                  onClick={() => setExpandedDriver(isExpanded ? null : d.driver_id)}
                  className={`w-full text-left px-4 py-3 flex items-center gap-3 transition-colors min-h-[52px] ${
                    isUser ? 'bg-red-950/20' : 'hover:bg-gray-700/30'
                  }`}
                >
                  {/* Position */}
                  <span className="text-gray-400 font-mono text-sm w-6 text-center flex-shrink-0">
                    {d.position ?? '-'}
                  </span>

                  {/* Driver code — always shown on mobile */}
                  <span className={`font-bold text-sm font-mono flex-shrink-0 ${isUser ? 'text-red-300' : 'text-white'}`}>
                    {d.driver_id.length <= 3 ? d.driver_id : d.driver_id.slice(0, 3).toUpperCase()}
                  </span>

                  {/* Full name — hidden on small mobile, shown from xs+ */}
                  <span className={`hidden xs:block text-sm flex-1 truncate ${isUser ? 'text-red-200' : 'text-gray-300'}`}>
                    {d.name}
                  </span>
                  <span className="flex-1 xs:hidden" />

                  {/* Badges */}
                  <div className="flex items-center gap-1.5">
                    {d.breakdown.fastest_lap && (
                      <span className="text-xs text-purple-400 font-bold">FL</span>
                    )}
                    {isUser && <span className="text-xs text-red-400 font-bold">★</span>}
                  </div>

                  {/* Fantasy points — bold + color + text label for accessibility */}
                  <span
                    className={`text-sm font-bold w-14 text-right flex-shrink-0 ${
                      ptsPositive ? 'text-green-400' : ptsNegative ? 'text-red-400' : 'text-gray-400'
                    }`}
                  >
                    {ptsPositive && <span className="mr-0.5">▲</span>}
                    {ptsNegative && <span className="mr-0.5">▼</span>}
                    {Math.abs(pts)}
                  </span>

                  {/* Expand indicator */}
                  <svg
                    className={`w-3 h-3 text-gray-500 flex-shrink-0 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                    fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                  </svg>
                </button>

                {/* ── Expanded breakdown ──────────────────────────── */}
                {isExpanded && (
                  <div className="bg-gray-700/30 px-4 py-3 grid grid-cols-2 gap-2 text-xs border-t border-gray-700">
                    <BreakdownItem label="Race pos pts" value={d.breakdown.race_position_points} />
                    <BreakdownItem label="Positions +" value={d.breakdown.positions_gained} />
                    <BreakdownItem label="Overtakes" value={d.breakdown.overtakes} />
                    <BreakdownItem label="Fastest lap" value={d.breakdown.fastest_lap ? 'Yes +10' : 'No'} />
                    <BreakdownItem label="DRS boost" value={d.breakdown.drs_boost_applied ? 'Active ×2' : 'Off'} />
                    <BreakdownItem label="Total" value={pts} bold />
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

function BreakdownItem({
  label, value, bold,
}: { label: string; value: string | number; bold?: boolean }) {
  return (
    <div className="flex justify-between">
      <span className="text-gray-400">{label}</span>
      <span className={`font-mono ${bold ? 'font-bold text-white' : 'text-gray-200'}`}>{value}</span>
    </div>
  )
}
