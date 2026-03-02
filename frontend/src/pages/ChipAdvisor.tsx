import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchRaces, fetchChipRecommendation } from '../lib/api'
import { useTeam } from '../hooks/useTeam'
import ChipRecommendationCard from '../components/ChipRecommendation'
import type { ChipRecommendation } from '../lib/types'

const ALL_CHIPS = ['DRS Boost', 'Extra DRS', 'No Negative', 'Wildcard', 'Limitless', 'Autopilot', 'Final Fix']

export default function ChipAdvisor() {
  const team = useTeam()
  const { data: races = [] } = useQuery({ queryKey: ['races'], queryFn: () => fetchRaces(2026) })

  const [selectedRaceId, setSelectedRaceId] = useState<number | null>(null)
  const [chipsRemaining, setChipsRemaining] = useState<string[]>(ALL_CHIPS)
  const [transfersBanked, setTransfersBanked] = useState(2)
  const [racesCompleted, setRacesCompleted] = useState(3)
  const [wetWeather, setWetWeather] = useState(false)
  const [recommendation, setRecommendation] = useState<ChipRecommendation | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const teamValue = team.totalSpent()
  const nextRace = races.find((r) => new Date(r.date) >= new Date())

  async function handleGetRecommendation() {
    const raceId = selectedRaceId ?? nextRace?.id
    if (!raceId) return

    setLoading(true)
    setError(null)
    try {
      const rec = await fetchChipRecommendation({
        race_id: raceId,
        chips_remaining: chipsRemaining,
        team_value: teamValue || 100_000_000,
        transfers_banked: transfersBanked,
        races_completed: racesCompleted,
        wet_weather_forecast: wetWeather,
      })
      setRecommendation(rec)
    } catch {
      setError('Failed to get recommendation')
    } finally {
      setLoading(false)
    }
  }

  function toggleChip(chip: string) {
    setChipsRemaining((prev) =>
      prev.includes(chip) ? prev.filter((c) => c !== chip) : [...prev, chip]
    )
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold text-white">Chip Advisor</h1>

      {/* On mobile: stacked layout; on md+: side-by-side */}
      <div className="grid md:grid-cols-2 gap-4">
        {/* Input form */}
        <div className="bg-gray-800 rounded-lg p-4 border border-gray-700 space-y-4">
          <h2 className="font-semibold text-white">Your Situation</h2>

          {/* Race selector */}
          <div>
            <label className="text-xs text-gray-400 block mb-1">Upcoming Race</label>
            <select
              value={selectedRaceId ?? nextRace?.id ?? ''}
              onChange={(e) => setSelectedRaceId(Number(e.target.value))}
              className="w-full min-h-[44px] bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-red-500"
            >
              {races.map((r) => (
                <option key={r.id} value={r.id}>
                  R{r.round_number}: {r.name}
                </option>
              ))}
            </select>
          </div>

          {/* Transfers banked */}
          <div>
            <label className="text-xs text-gray-400 block mb-1">
              Transfers banked: <span className="text-white font-medium">{transfersBanked}</span>
            </label>
            <input
              type="range"
              min={0}
              max={5}
              value={transfersBanked}
              onChange={(e) => setTransfersBanked(Number(e.target.value))}
              className="w-full h-2 accent-red-500"
            />
          </div>

          {/* Races completed */}
          <div>
            <label className="text-xs text-gray-400 block mb-1">
              Races completed: <span className="text-white font-medium">{racesCompleted}</span>
            </label>
            <input
              type="range"
              min={0}
              max={24}
              value={racesCompleted}
              onChange={(e) => setRacesCompleted(Number(e.target.value))}
              className="w-full h-2 accent-red-500"
            />
          </div>

          {/* Team value */}
          <div className="text-sm text-gray-400">
            Team value:{' '}
            <span className="text-white font-medium">
              ${((teamValue || 100_000_000) / 1e6).toFixed(1)}M
            </span>
            {teamValue === 0 && (
              <span className="text-yellow-500 ml-1 text-xs">(no team selected)</span>
            )}
          </div>

          {/* Wet weather */}
          <label className="flex items-center gap-3 text-sm cursor-pointer min-h-[44px]">
            <input
              type="checkbox"
              checked={wetWeather}
              onChange={(e) => setWetWeather(e.target.checked)}
              className="w-4 h-4 rounded accent-red-500"
            />
            <span className="text-gray-300">Wet weather forecast</span>
          </label>

          {/* Chips remaining — scrollable pills */}
          <div>
            <label className="text-xs text-gray-400 block mb-2">
              Chips remaining ({chipsRemaining.length}/{ALL_CHIPS.length}):
            </label>
            <div className="flex flex-wrap gap-2">
              {ALL_CHIPS.map((chip) => (
                <button
                  key={chip}
                  onClick={() => toggleChip(chip)}
                  className={`min-h-[40px] px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                    chipsRemaining.includes(chip)
                      ? 'border-green-600 bg-green-900/30 text-green-400'
                      : 'border-gray-600 bg-gray-700/50 text-gray-500'
                  }`}
                >
                  {chip}
                </button>
              ))}
            </div>
          </div>

          {error && <p className="text-red-400 text-sm font-medium">{error}</p>}

          <button
            onClick={handleGetRecommendation}
            disabled={loading || chipsRemaining.length === 0}
            className="w-full min-h-[52px] bg-red-600 hover:bg-red-500 text-white font-semibold rounded-lg text-base disabled:opacity-50 transition-colors"
          >
            {loading ? 'Analysing...' : 'Get Recommendation'}
          </button>
        </div>

        {/* Recommendation output — full width on mobile */}
        <div>
          {recommendation ? (
            <ChipRecommendationCard recommendation={recommendation} />
          ) : (
            <div className="bg-gray-800 rounded-lg p-6 text-center border border-gray-700 min-h-[200px] flex flex-col items-center justify-center">
              <p className="text-gray-400 text-sm">Fill in your situation and tap</p>
              <p className="text-gray-300 text-sm font-semibold mt-1">"Get Recommendation"</p>
              <p className="text-gray-600 text-xs mt-3 max-w-[240px]">
                The advisor uses your circuit type, chip inventory, and team state.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
