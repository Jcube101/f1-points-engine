import { useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer, CartesianGrid,
} from 'recharts'
import { fetchTeammateComparison } from '../lib/api'
import type { TeammateStats } from '../lib/types'

interface Props {
  constructorId: number | null
  onClose: () => void
}

function StatRow({ label, v1, v2, lowerIsBetter = false }: {
  label: string
  v1: number | string
  v2: number | string
  lowerIsBetter?: boolean
}) {
  const n1 = typeof v1 === 'number' ? v1 : null
  const n2 = typeof v2 === 'number' ? v2 : null
  const d1Better = n1 != null && n2 != null && (lowerIsBetter ? n1 < n2 : n1 > n2)
  const d2Better = n1 != null && n2 != null && (lowerIsBetter ? n2 < n1 : n2 > n1)
  return (
    <tr className="border-b border-gray-700/40">
      <td className={`py-2 px-2 text-right text-sm font-medium ${d1Better ? 'text-green-400' : 'text-white'}`}>
        {typeof v1 === 'number' ? v1.toFixed(1) : v1}
      </td>
      <td className="py-2 px-2 text-center text-xs text-gray-500 whitespace-nowrap">{label}</td>
      <td className={`py-2 px-2 text-left text-sm font-medium ${d2Better ? 'text-green-400' : 'text-white'}`}>
        {typeof v2 === 'number' ? v2.toFixed(1) : v2}
      </td>
    </tr>
  )
}

function DriverStats({ d }: { d: TeammateStats }) {
  return (
    <div className="text-center">
      <p className="font-bold text-white text-base">{d.code}</p>
      <p className="text-xs text-gray-400 truncate max-w-[120px] mx-auto">{d.name}</p>
      <p className="text-xs text-green-400">${(d.price / 1_000_000).toFixed(1)}M</p>
    </div>
  )
}

export default function TeammateModal({ constructorId, onClose }: Props) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['teammates', constructorId],
    queryFn: () => fetchTeammateComparison(constructorId!),
    enabled: constructorId != null,
  })

  // Close on Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  if (constructorId == null) return null

  const d1 = data?.driver_1
  const d2 = data?.driver_2

  const chartData = d1 && d2
    ? [
        { metric: 'Avg Pts', [d1.code]: parseFloat(d1.avg_fantasy_pts.toFixed(1)), [d2.code]: parseFloat(d2.avg_fantasy_pts.toFixed(1)) },
        { metric: 'xP', [d1.code]: parseFloat(d1.xp.toFixed(1)), [d2.code]: parseFloat(d2.xp.toFixed(1)) },
        { metric: 'Pts/$M', [d1.code]: parseFloat(d1.pts_per_million.toFixed(1)), [d2.code]: parseFloat(d2.pts_per_million.toFixed(1)) },
      ]
    : []

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/60 z-40"
        onClick={onClose}
      />

      {/* Bottom sheet on mobile, centered modal on desktop */}
      <div className="fixed z-50 bottom-0 left-0 right-0 sm:inset-0 sm:flex sm:items-center sm:justify-center sm:p-4">
        <div className="bg-gray-900 rounded-t-2xl sm:rounded-2xl border border-gray-700 w-full sm:max-w-lg max-h-[85vh] overflow-y-auto">
          {/* Handle (mobile) */}
          <div className="flex justify-center pt-3 sm:hidden">
            <div className="w-10 h-1 bg-gray-600 rounded-full" />
          </div>

          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700">
            <h2 className="font-bold text-white text-base">Teammate Comparison</h2>
            <button
              onClick={onClose}
              className="min-h-[44px] min-w-[44px] flex items-center justify-center text-gray-400 hover:text-white rounded-lg"
            >
              ✕
            </button>
          </div>

          <div className="p-4 space-y-4">
            {isLoading && (
              <p className="text-gray-400 text-sm text-center py-6">Loading comparison...</p>
            )}
            {isError && (
              <p className="text-red-400 text-sm text-center py-6">Failed to load data.</p>
            )}
            {data === null && !isLoading && (
              <p className="text-gray-400 text-sm text-center py-6">Not enough data for comparison.</p>
            )}

            {d1 && d2 && (
              <>
                {/* Driver headers */}
                <div className="grid grid-cols-3 items-center">
                  <DriverStats d={d1} />
                  <p className="text-center text-gray-500 text-xs">vs</p>
                  <DriverStats d={d2} />
                </div>

                {/* H2H summary */}
                <div className="bg-gray-800 rounded-lg p-3 text-center">
                  <p className="text-xs text-gray-400">
                    H2H Qualifying ({data.h2h_qualifying_races} shared races):
                    <span className="text-white font-medium ml-1">{d1.code} {d1.quali_h2h_wins} – {d2.quali_h2h_wins} {d2.code}</span>
                  </p>
                </div>

                {/* Stats table */}
                <table className="w-full">
                  <tbody>
                    <StatRow label="Avg Fantasy Pts" v1={d1.avg_fantasy_pts} v2={d2.avg_fantasy_pts} />
                    <StatRow label="Total Fantasy Pts" v1={d1.total_fantasy_pts} v2={d2.total_fantasy_pts} />
                    <StatRow label="xP" v1={d1.xp} v2={d2.xp} />
                    <StatRow label="Pts per $M" v1={d1.pts_per_million} v2={d2.pts_per_million} />
                    <StatRow label="Avg Quali Pos" v1={d1.avg_qualifying_pos} v2={d2.avg_qualifying_pos} lowerIsBetter />
                    <StatRow label="Avg Race Pos" v1={d1.avg_race_pos} v2={d2.avg_race_pos} lowerIsBetter />
                  </tbody>
                </table>

                {/* Bar chart */}
                <div>
                  <p className="text-xs text-gray-400 mb-2">Key metrics comparison</p>
                  <ResponsiveContainer width="100%" height={160}>
                    <BarChart data={chartData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                      <XAxis dataKey="metric" tick={{ fill: '#9CA3AF', fontSize: 10 }} />
                      <YAxis tick={{ fill: '#9CA3AF', fontSize: 10 }} />
                      <Tooltip contentStyle={{ backgroundColor: '#1F2937', border: 'none', borderRadius: '8px', fontSize: 11 }} />
                      <Legend wrapperStyle={{ fontSize: 11 }} />
                      <Bar dataKey={d1.code} fill="#E8002D" radius={[3, 3, 0, 0]} />
                      <Bar dataKey={d2.code} fill="#3671C6" radius={[3, 3, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </>
  )
}
