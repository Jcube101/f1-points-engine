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
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Live Race</h1>
        <div className="flex items-center gap-2 text-sm">
          <span className={`w-2 h-2 rounded-full ${connected ? 'bg-green-500' : 'bg-red-500'}`} />
          <span className="text-gray-400">{connected ? 'Connected' : 'Disconnected'}</span>
        </div>
      </div>

      {error && (
        <div className="bg-red-950/30 border border-red-700 rounded-lg p-3 text-sm text-red-400">
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
            Your team: <span className="text-white">{userDriverCodes.join(' · ')}</span>
            <span className="text-gray-600 ml-2">(highlighted with ★)</span>
          </p>
        </div>
      )}
    </div>
  )
}
