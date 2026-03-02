import { useQuery } from '@tanstack/react-query'
import { fetchLiveStatus } from '../lib/api'
import { useLiveRace } from '../hooks/useLiveRace'
import { useTeam } from '../hooks/useTeam'
import LiveTicker from '../components/LiveTicker'

export default function LiveRace() {
  const { snapshot, connected, error } = useLiveRace()
  const { data: status } = useQuery({
    queryKey: ['liveStatus'],
    queryFn: fetchLiveStatus,
    refetchInterval: 30_000,
  })

  const team = useTeam()
  const userDriverCodes = team.drivers.map((d) => d.code)

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Live Race</h1>
        <div className="flex items-center gap-2 text-sm">
          <span className={`w-2.5 h-2.5 rounded-full ${connected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
          <span className="text-gray-400 text-xs font-medium">{connected ? 'Connected' : 'Disconnected'}</span>
        </div>
      </div>

      {error && (
        <div className="bg-red-950/30 border border-red-700 rounded-lg p-3 text-sm text-red-400 font-medium">
          {error}
        </div>
      )}

      {!status?.is_live && !snapshot && (
        <div className="bg-gray-800 rounded-lg p-6 text-center border border-gray-700">
          <h2 className="text-lg font-semibold text-white mb-2">No Active Session</h2>
          <p className="text-gray-400 text-sm">
            Live fantasy points appear here during qualifying, sprint, and race sessions.
          </p>
          <p className="text-gray-500 text-xs mt-2">
            The WebSocket auto-connects — no manual refresh needed.
          </p>
        </div>
      )}

      {(status?.is_live || snapshot) && (
        <LiveTicker snapshot={snapshot} userDriverCodes={userDriverCodes} />
      )}

      {userDriverCodes.length > 0 && (
        <div className="bg-gray-800 rounded-lg p-3 border border-gray-700 text-sm">
          <p className="text-gray-400">
            Your team: <span className="text-white font-medium">{userDriverCodes.join(' · ')}</span>
            <span className="text-gray-600 ml-2 text-xs">(rows marked ★)</span>
          </p>
        </div>
      )}

      {/* Tap-to-expand hint */}
      {snapshot && (
        <p className="text-xs text-gray-600 text-center">Tap any row to see full points breakdown</p>
      )}
    </div>
  )
}
