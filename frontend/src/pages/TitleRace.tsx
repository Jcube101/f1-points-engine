import { useState, useCallback, useRef, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
} from 'recharts'
import { fetchWDC, fetchTitleOdds } from '../lib/api'
import type { TitleOddsEntry } from '../lib/types'

const TEAM_COLORS: Record<string, string> = {
  VER: '#3671C6', HAD: '#3671C6',
  NOR: '#FF8000', PIA: '#FF8000',
  LEC: '#E8002D', HAM: '#E8002D',
  RUS: '#27F4D2', ANT: '#27F4D2',
  GAS: '#FF87BC', COL: '#FF87BC',
  SAI: '#64C4FF', ALB: '#64C4FF',
  ALO: '#229971', STR: '#229971',
  BEA: '#B6BABD', OCO: '#B6BABD',
  HUL: '#52E252', BOR: '#52E252',
  LAW: '#6692FF', LIN: '#6692FF',
  PER: '#CC0033', BOT: '#CC0033',
}

function ProbBar({ entry }: { entry: TitleOddsEntry }) {
  const pct = Math.round(entry.win_probability * 100)
  const color = TEAM_COLORS[entry.driver_code] ?? '#888'
  return (
    <div className="flex items-center gap-3">
      <span className="text-gray-400 text-xs font-mono w-8 text-right">{entry.driver_code}</span>
      <div className="flex-1 bg-gray-800 rounded-full h-5 overflow-hidden">
        <div
          className="h-full rounded-full flex items-center pl-2 text-xs font-bold text-white"
          style={{ width: `${Math.max(pct, 2)}%`, backgroundColor: color, transition: 'width 0.4s' }}
        >
          {pct >= 5 ? `${pct}%` : ''}
        </div>
      </div>
      <span className="text-gray-300 text-xs w-10 text-right">{pct}%</span>
    </div>
  )
}

/** Animate a fake progress bar from 0→93% over ~4s, then caller snaps to 100. */
function useSimProgress(active: boolean) {
  const [progress, setProgress] = useState(0)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    if (active) {
      setProgress(0)
      const start = Date.now()
      const DURATION = 4000 // ms — approximate compute time
      timerRef.current = setInterval(() => {
        const elapsed = Date.now() - start
        // Ease-out: fast at start, slows near 93%
        const raw = elapsed / DURATION
        const eased = 1 - Math.pow(1 - Math.min(raw, 1), 2)
        setProgress(Math.min(Math.round(eased * 93), 93))
      }, 80)
    } else {
      if (timerRef.current) clearInterval(timerRef.current)
      // Caller sets to 100 when done; let it settle then reset
    }
    return () => { if (timerRef.current) clearInterval(timerRef.current) }
  }, [active])

  return progress
}

export default function TitleRace() {
  const [paceMultipliers, setPaceMultipliers] = useState<Record<string, number>>({})
  const [simResult, setSimResult] = useState<TitleOddsEntry[] | null>(null)
  const [summary, setSummary] = useState<string>('')
  const [remainingRaces, setRemainingRaces] = useState<number>(0)
  const [simulating, setSimulating] = useState(false)
  const [simProgress, setSimProgress] = useState(0)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const fakeProgress = useSimProgress(simulating)

  // While simulating use the animated progress; show 100 briefly when done
  const displayProgress = simulating ? fakeProgress : simProgress

  // Live WDC standings
  const { data: standings, isLoading: standingsLoading } = useQuery({
    queryKey: ['wdc', 2026],
    queryFn: () => fetchWDC(2026),
  })

  // Initial simulation on page load
  const { data: initialOdds, isLoading: oddsLoading } = useQuery({
    queryKey: ['titleOdds', 2026],
    queryFn: () => fetchTitleOdds(2026, []),
  })

  useEffect(() => {
    if (initialOdds && !simResult) {
      setSimResult(initialOdds.odds)
      setSummary(initialOdds.scenario_summary)
      setRemainingRaces(initialOdds.remaining_races)
    }
  }, [initialOdds, simResult])

  const top5codes = (simResult ?? initialOdds?.odds ?? []).slice(0, 5).map(e => e.driver_code)

  const runWithPace = useCallback(async (multipliers: Record<string, number>) => {
    setSimulating(true)
    setSimProgress(0)
    try {
      const paceList = Object.entries(multipliers)
        .filter(([, v]) => v !== 1.0)
        .map(([driver_code, multiplier]) => ({ driver_code, multiplier }))
      const result = await fetchTitleOdds(2026, paceList)
      setSimProgress(100)
      setSimResult(result.odds)
      setSummary(result.scenario_summary)
      setRemainingRaces(result.remaining_races)
    } finally {
      setSimulating(false)
    }
  }, [])

  const handleSlider = (code: string, val: number) => {
    const updated = { ...paceMultipliers, [code]: val }
    setPaceMultipliers(updated)
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => runWithPace(updated), 350)
  }

  const displayOdds = simResult ?? initialOdds?.odds ?? []
  const loading = standingsLoading || oddsLoading

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-white">🏆 Title Race</h1>

      {/* Section A: Live Championship Standings */}
      <section className="bg-gray-900 rounded-xl p-4 space-y-3">
        <h2 className="text-lg font-semibold text-white">Championship Standings</h2>
        {standingsLoading ? (
          <p className="text-gray-400 text-sm">Loading standings…</p>
        ) : !standings || standings.length === 0 ? (
          <p className="text-gray-400 text-sm">Season hasn't started yet — standings will appear after R1.</p>
        ) : (
          <>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart
                data={standings.slice(0, 10)}
                layout="vertical"
                margin={{ left: 60, right: 30, top: 4, bottom: 4 }}
              >
                <XAxis type="number" tick={{ fill: '#9ca3af', fontSize: 11 }} />
                <YAxis
                  type="category"
                  dataKey="driver_code"
                  tick={{ fill: '#d1d5db', fontSize: 12 }}
                  width={56}
                />
                <Tooltip
                  formatter={(v: number) => [`${v} pts`, 'Points']}
                  contentStyle={{ background: '#111827', border: '1px solid #374151', color: '#f9fafb' }}
                />
                <Bar dataKey="points" radius={[0, 4, 4, 0]}>
                  {standings.slice(0, 10).map((s) => (
                    <Cell key={s.driver_code} fill={TEAM_COLORS[s.driver_code] ?? '#6b7280'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
            <div className="space-y-1">
              {standings.slice(0, 10).map((s, i) => (
                <div key={s.driver_code} className="flex items-center gap-3 text-sm">
                  <span className="text-gray-500 w-5 text-right">{i + 1}</span>
                  <span
                    className="font-mono font-bold w-10"
                    style={{ color: TEAM_COLORS[s.driver_code] ?? '#9ca3af' }}
                  >
                    {s.driver_code}
                  </span>
                  <span className="text-gray-300 flex-1">{s.driver_name}</span>
                  <span className="text-white font-semibold">{s.points} pts</span>
                  {s.wins > 0 && <span className="text-yellow-400 text-xs">{s.wins}W</span>}
                </div>
              ))}
            </div>
          </>
        )}
      </section>

      {/* Section B: Monte Carlo Odds Calculator */}
      <section className="bg-gray-900 rounded-xl p-4 space-y-4">
        <h2 className="text-lg font-semibold text-white">Monte Carlo Odds Calculator</h2>

        {/* Progress bar — shown during initial load or slider re-simulation */}
        {(loading || simulating) && (
          <div className="space-y-2">
            <p className="text-gray-400 text-sm">Running 10,000 simulations…</p>
            <div className="h-3 bg-gray-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-red-600 rounded-full transition-all duration-150"
                style={{ width: `${loading ? fakeProgress : displayProgress}%` }}
              />
            </div>
            <p className="text-gray-500 text-xs text-right">
              {loading ? fakeProgress : displayProgress}%
            </p>
          </div>
        )}

        {!loading && (
          <>
            {remainingRaces > 0 && (
              <p className="text-gray-400 text-xs">{remainingRaces} races remaining · 10,000 simulations</p>
            )}

            {/* Win probability bars */}
            <div className="space-y-2">
              {displayOdds.slice(0, 10).map((entry) => (
                <ProbBar key={entry.driver_code} entry={entry} />
              ))}
            </div>

            {/* Scenario summary */}
            {summary && (
              <div className="bg-gray-800 rounded-lg p-3 text-sm text-gray-300 leading-relaxed border-l-4 border-red-500">
                {summary}
              </div>
            )}

            {/* Pace sliders for top 5 */}
            {top5codes.length > 0 && (
              <div className="pt-2 space-y-3">
                <h3 className="text-sm font-semibold text-gray-300">Adjust Pace Expectations</h3>
                {top5codes.map((code) => {
                  const val = paceMultipliers[code] ?? 1.0
                  return (
                    <div key={code} className="flex items-center gap-3 min-h-[44px]">
                      <span
                        className="font-mono text-sm font-bold w-10"
                        style={{ color: TEAM_COLORS[code] ?? '#9ca3af' }}
                      >
                        {code}
                      </span>
                      <input
                        type="range"
                        min={0.5}
                        max={1.5}
                        step={0.05}
                        value={val}
                        onChange={(e) => handleSlider(code, parseFloat(e.target.value))}
                        className="flex-1 accent-red-500 min-h-[44px]"
                      />
                      <span className="text-gray-400 text-xs w-10 text-right">{val.toFixed(2)}×</span>
                    </div>
                  )
                })}
                <button
                  onClick={() => {
                    setPaceMultipliers({})
                    runWithPace({})
                  }}
                  className="min-h-[44px] px-3 inline-flex items-center text-xs text-gray-500 hover:text-gray-300 transition-colors"
                >
                  Reset sliders
                </button>
              </div>
            )}
          </>
        )}
      </section>
    </div>
  )
}
