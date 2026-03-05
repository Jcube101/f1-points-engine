import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import type { Driver } from '../lib/types'
import { fetchDriverForm } from '../lib/api'

interface Props {
  driver: Driver
  selected?: boolean
  onSelect?: (driver: Driver) => void
  showXP?: boolean
}

export default function DriverCard({ driver, selected, onSelect, showXP = true }: Props) {
  const priceM = (driver.price / 1_000_000).toFixed(1)
  const [expanded, setExpanded] = useState(false)

  const { data: formData, isLoading: formLoading } = useQuery({
    queryKey: ['driverForm', driver.id],
    queryFn: () => fetchDriverForm(driver.id),
    enabled: expanded,
  })

  const formBadge = driver.form_status === 'overperforming'
    ? { label: '🔴 Sell signal', cls: 'bg-red-900/60 text-red-300 border-red-700' }
    : driver.form_status === 'underperforming'
    ? { label: '🟢 Buy signal', cls: 'bg-green-900/60 text-green-300 border-green-700' }
    : null

  const circuitFitColor =
    driver.circuit_fit_score != null
      ? driver.circuit_fit_score >= 7 ? 'text-green-400'
      : driver.circuit_fit_score >= 4 ? 'text-yellow-400'
      : 'text-red-400'
      : null

  return (
    <div
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && onSelect?.(driver)}
      className={`
        relative rounded-lg border min-h-[72px] transition-all
        ${selected
          ? 'border-red-500 bg-red-950/30'
          : 'border-gray-700 bg-gray-800 hover:border-gray-500'
        }
        ${onSelect ? 'cursor-pointer' : ''}
      `}
    >
      {/* Team color bar */}
      <div
        className="absolute top-0 left-0 w-1 h-full rounded-l-lg"
        style={{ backgroundColor: driver.team_color }}
      />

      {/* Main content — clickable area for select */}
      <div
        className="pl-3 pr-3 pt-3 pb-2"
        onClick={() => onSelect?.(driver)}
      >
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <div className="flex items-center gap-1.5 flex-wrap">
              <p className="font-semibold text-sm text-white leading-tight">{driver.name}</p>
              {driver.is_differential && (
                <span className="text-xs font-bold text-yellow-400" title="Differential pick">⚡</span>
              )}
            </div>
            <p className="text-xs text-gray-400 mt-0.5">{driver.team_name}</p>
          </div>
          <div className="text-right flex-shrink-0">
            <p className="text-sm font-bold text-green-400">${priceM}M</p>
            {showXP && (
              <p className="text-xs text-blue-400">xP: {driver.xp.toFixed(1)}</p>
            )}
          </div>
        </div>

        <div className="mt-2 flex justify-between text-xs text-gray-400">
          <span>Code: <span className="text-white font-mono">{driver.code}</span></span>
          <span>Val: <span className="text-yellow-400">{driver.value_score.toFixed(2)}</span></span>
        </div>

        {/* Badges row */}
        <div className="mt-2 flex flex-wrap gap-1.5 items-center">
          {formBadge && (
            <span className={`text-xs px-1.5 py-0.5 rounded border font-medium ${formBadge.cls}`}>
              {formBadge.label}
            </span>
          )}
          {circuitFitColor && driver.circuit_fit_type && (
            <span className={`text-xs font-medium ${circuitFitColor}`}>
              {driver.circuit_fit_type} fit: {driver.circuit_fit_score?.toFixed(1)}
            </span>
          )}
        </div>

        {selected && (
          <div className="mt-1 text-xs text-red-400 font-medium">Selected</div>
        )}
      </div>

      {/* Expand sparkline button */}
      <button
        onClick={(e) => { e.stopPropagation(); setExpanded((v) => !v) }}
        className="w-full border-t border-gray-700/50 py-1.5 text-xs text-gray-500 hover:text-gray-300 transition-colors min-h-[32px] flex items-center justify-center gap-1"
      >
        {expanded ? '▲ Hide trend' : '▼ Show form trend'}
      </button>

      {/* Sparkline panel */}
      {expanded && (
        <div className="border-t border-gray-700/50 px-3 pb-3 pt-2">
          {formLoading ? (
            <p className="text-xs text-gray-500 text-center py-2">Loading...</p>
          ) : formData && formData.history.length > 0 ? (
            <>
              <p className="text-xs text-gray-400 mb-2">
                Actual vs xP — last {formData.history.length} races
                {formData.flag !== 'on_form' && (
                  <span className={`ml-2 font-medium ${formData.flag === 'overperforming' ? 'text-red-400' : 'text-green-400'}`}>
                    ({formData.flag === 'overperforming' ? 'overperforming' : 'underperforming'} by {Math.abs(formData.delta).toFixed(1)} pts avg)
                  </span>
                )}
              </p>
              <div className="overflow-x-auto -mx-1">
                <div className="min-w-[260px] px-1">
                  <ResponsiveContainer width="100%" height={100}>
                    <AreaChart data={formData.history} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                      <defs>
                        <linearGradient id={`xpGrad-${driver.id}`} x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.3} />
                          <stop offset="95%" stopColor="#3B82F6" stopOpacity={0} />
                        </linearGradient>
                        <linearGradient id={`actGrad-${driver.id}`} x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#10B981" stopOpacity={0.3} />
                          <stop offset="95%" stopColor="#10B981" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <XAxis dataKey="round" tick={{ fill: '#6B7280', fontSize: 9 }} />
                      <YAxis tick={{ fill: '#6B7280', fontSize: 9 }} />
                      <Tooltip
                        contentStyle={{ backgroundColor: '#1F2937', border: 'none', borderRadius: '6px', fontSize: 11 }}
                        formatter={(value: number, name: string) => [value.toFixed(1), name === 'xp' ? 'xP' : 'Actual']}
                        labelFormatter={(label) => `Round ${label}`}
                      />
                      <Area type="monotone" dataKey="xp" stroke="#3B82F6" strokeWidth={1.5} fill={`url(#xpGrad-${driver.id})`} dot={false} name="xp" />
                      <Area type="monotone" dataKey="actual" stroke="#10B981" strokeWidth={1.5} fill={`url(#actGrad-${driver.id})`} dot={false} name="actual" />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>
              <div className="flex gap-3 mt-1 text-xs">
                <span className="flex items-center gap-1"><span className="w-2 h-0.5 bg-blue-500 inline-block" /> xP</span>
                <span className="flex items-center gap-1"><span className="w-2 h-0.5 bg-emerald-500 inline-block" /> Actual</span>
              </div>
            </>
          ) : (
            <p className="text-xs text-gray-500 text-center py-2">No form data available</p>
          )}
        </div>
      )}
    </div>
  )
}
