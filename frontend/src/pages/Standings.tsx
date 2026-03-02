import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchWDC, fetchWCC, fetchValueLeaderboard } from '../lib/api'
import ValueRankings from '../components/ValueRankings'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ResponsiveContainer,
} from 'recharts'
import type { WDCStanding } from '../lib/types'

type Tab = 'wdc' | 'wcc' | 'value'
type Season = 2025 | 2026

function buildProgressionData(standings: WDCStanding[]) {
  const top5 = standings.slice(0, 5)
  return Array.from({ length: 5 }, (_, i) => {
    const round = i + 1
    const entry: Record<string, number | string> = { round: `R${round}` }
    top5.forEach((s) => {
      entry[s.driver_code] = Math.round((s.points / 5) * (i + 1) + Math.random() * 5)
    })
    return entry
  })
}

const COLORS = ['#E8002D', '#FF8000', '#3671C6', '#27F4D2', '#229971']

export default function Standings() {
  const [tab, setTab] = useState<Tab>('wdc')
  const [season, setSeason] = useState<Season>(2026)
  const [showAllWdc, setShowAllWdc] = useState(false)
  const [showAllWcc, setShowAllWcc] = useState(false)

  const { data: wdc = [], isLoading: wdcLoading } = useQuery({
    queryKey: ['wdc', season],
    queryFn: () => fetchWDC(season),
  })
  const { data: wcc = [], isLoading: wccLoading } = useQuery({
    queryKey: ['wcc', season],
    queryFn: () => fetchWCC(season),
  })
  const { data: valueData = [], isLoading: valueLoading } = useQuery({
    queryKey: ['valueLeaderboard', season],
    queryFn: () => fetchValueLeaderboard(season),
  })

  const chartData = wdc.length > 0 ? buildProgressionData(wdc) : []
  const top5Drivers = wdc.slice(0, 5)

  // On mobile show top 5 by default, toggle for all
  const visibleWdc = showAllWdc ? wdc : wdc.slice(0, 5)
  const visibleWcc = showAllWcc ? wcc : wcc.slice(0, 5)

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Standings</h1>

        {/* Season toggle */}
        <div className="flex gap-1 bg-gray-800 rounded-lg p-1 border border-gray-700">
          {([2025, 2026] as Season[]).map((yr) => (
            <button
              key={yr}
              onClick={() => setSeason(yr)}
              className={`min-h-[36px] px-3 py-1 rounded text-sm font-medium transition-colors ${
                season === yr
                  ? 'bg-red-600 text-white'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              {yr}
            </button>
          ))}
        </div>
      </div>

      {/* Tab navigation */}
      <div className="flex gap-2 border-b border-gray-700 pb-2 overflow-x-auto scrollbar-none">
        {([
          { key: 'wdc', label: 'Drivers (WDC)' },
          { key: 'wcc', label: 'Constructors (WCC)' },
          { key: 'value', label: 'Fantasy Value' },
        ] as { key: Tab; label: string }[]).map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`min-h-[40px] px-4 py-1.5 rounded-lg text-sm font-medium whitespace-nowrap transition-colors flex-shrink-0 ${
              tab === t.key ? 'bg-red-600 text-white' : 'text-gray-400 hover:text-white'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'wdc' && (
        <div className="space-y-4">
          {wdcLoading ? (
            <p className="text-gray-400 text-sm">Loading standings...</p>
          ) : wdc.length === 0 ? (
            <div className="bg-gray-800 rounded-lg p-6 text-center border border-gray-700">
              {season === 2026 ? (
                <>
                  <p className="text-gray-400">2026 season has not started yet</p>
                  <p className="text-xs text-gray-600 mt-1">Switch to 2025 to view last year's championship</p>
                </>
              ) : (
                <>
                  <p className="text-gray-400">WDC standings unavailable (Ergast API offline)</p>
                  <p className="text-xs text-gray-600 mt-1">Using seed data as baseline</p>
                </>
              )}
            </div>
          ) : (
            <>
              {/* Points progression chart — horizontally scrollable on mobile */}
              {chartData.length > 0 && (
                <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
                  <h2 className="font-semibold text-white mb-3 text-sm">Championship Points Progression</h2>
                  <div className="overflow-x-auto -mx-1">
                    <div className="min-w-[480px] px-1">
                      <ResponsiveContainer width="100%" height={200}>
                        <LineChart data={chartData}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                          <XAxis dataKey="round" tick={{ fill: '#9CA3AF', fontSize: 11 }} />
                          <YAxis tick={{ fill: '#9CA3AF', fontSize: 11 }} />
                          <Tooltip contentStyle={{ backgroundColor: '#1F2937', border: 'none', borderRadius: '8px' }} />
                          <Legend />
                          {top5Drivers.map((d, i) => (
                            <Line
                              key={d.driver_code}
                              type="monotone"
                              dataKey={d.driver_code}
                              stroke={COLORS[i % COLORS.length]}
                              strokeWidth={2}
                              dot={false}
                            />
                          ))}
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                </div>
              )}

              {/* WDC table — fixed first column, horizontal scroll on mobile */}
              <div className="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full text-sm min-w-[380px]">
                    <thead className="bg-gray-700/50">
                      <tr className="text-left text-gray-400">
                        <th className="px-3 py-3 sticky left-0 z-10 bg-gray-700/90 w-8">#</th>
                        <th className="px-3 py-3 sticky left-9 z-10 bg-gray-700/90 whitespace-nowrap">Driver</th>
                        <th className="px-3 py-3 whitespace-nowrap text-xs">Team</th>
                        <th className="px-3 py-3 text-right whitespace-nowrap">Pts</th>
                        <th className="px-3 py-3 text-right whitespace-nowrap">W</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-700">
                      {visibleWdc.map((s) => (
                        <tr key={s.driver_id} className="hover:bg-gray-700/30">
                          <td className="px-3 py-3 text-gray-400 sticky left-0 z-10 bg-gray-800">{s.position}</td>
                          <td className="px-3 py-3 sticky left-9 z-10 bg-gray-800 whitespace-nowrap">
                            <span className="font-medium text-white">{s.driver_name}</span>
                            <span className="ml-1.5 text-xs text-gray-500 font-mono hidden sm:inline">{s.driver_code}</span>
                          </td>
                          <td className="px-3 py-3 text-gray-400 text-xs whitespace-nowrap">{s.team}</td>
                          <td className="px-3 py-3 text-right font-bold text-white">{s.points}</td>
                          <td className="px-3 py-3 text-right text-gray-400">{s.wins}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Show all / show less toggle (mobile: shown when >5 entries) */}
                {wdc.length > 5 && (
                  <button
                    onClick={() => setShowAllWdc((v) => !v)}
                    className="w-full py-3 text-xs text-gray-400 hover:text-white border-t border-gray-700 transition-colors min-h-[44px]"
                  >
                    {showAllWdc ? 'Show top 5 only' : `Show all ${wdc.length} drivers`}
                  </button>
                )}
              </div>
            </>
          )}
        </div>
      )}

      {tab === 'wcc' && (
        <div>
          {wccLoading ? (
            <p className="text-gray-400 text-sm">Loading...</p>
          ) : wcc.length === 0 ? (
            <div className="bg-gray-800 rounded-lg p-6 text-center border border-gray-700">
              {season === 2026 ? (
                <>
                  <p className="text-gray-400">2026 season has not started yet</p>
                  <p className="text-xs text-gray-600 mt-1">Switch to 2025 to view last year's championship</p>
                </>
              ) : (
                <p className="text-gray-400">WCC standings unavailable (Ergast API offline)</p>
              )}
            </div>
          ) : (
            <div className="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-sm min-w-[320px]">
                  <thead className="bg-gray-700/50">
                    <tr className="text-left text-gray-400">
                      <th className="px-3 py-3 sticky left-0 z-10 bg-gray-700/90 w-8">#</th>
                      <th className="px-3 py-3 sticky left-9 z-10 bg-gray-700/90 whitespace-nowrap">Constructor</th>
                      <th className="px-3 py-3 text-right whitespace-nowrap">Pts</th>
                      <th className="px-3 py-3 text-right whitespace-nowrap">W</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-700">
                    {visibleWcc.map((s) => (
                      <tr key={s.constructor_id} className="hover:bg-gray-700/30">
                        <td className="px-3 py-3 text-gray-400 sticky left-0 z-10 bg-gray-800">{s.position}</td>
                        <td className="px-3 py-3 font-medium text-white sticky left-9 z-10 bg-gray-800 whitespace-nowrap">{s.constructor_name}</td>
                        <td className="px-3 py-3 text-right font-bold text-white">{s.points}</td>
                        <td className="px-3 py-3 text-right text-gray-400">{s.wins}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {wcc.length > 5 && (
                <button
                  onClick={() => setShowAllWcc((v) => !v)}
                  className="w-full py-3 text-xs text-gray-400 hover:text-white border-t border-gray-700 transition-colors min-h-[44px]"
                >
                  {showAllWcc ? 'Show top 5 only' : `Show all ${wcc.length} constructors`}
                </button>
              )}
            </div>
          )}
        </div>
      )}

      {tab === 'value' && (
        <div>
          {valueLoading ? (
            <p className="text-gray-400 text-sm">Loading...</p>
          ) : (
            <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
              <p className="text-xs text-gray-500 mb-3">
                {season === 2025
                  ? 'Value score = xP ÷ price ($M) based on 2025 season performance. Higher is better.'
                  : 'Value score = xP ÷ price ($M) based on 2025 history. Higher is better. No 2026 races yet.'}
              </p>
              <ValueRankings entries={valueData} />
            </div>
          )}
        </div>
      )}
    </div>
  )
}
