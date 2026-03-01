import type { LiveSnapshot } from '../lib/types'

interface Props {
  snapshot: LiveSnapshot | null
  userDriverCodes?: string[]
}

export default function LiveTicker({ snapshot, userDriverCodes = [] }: Props) {
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
    <div className="space-y-4">
      {/* Session header */}
      <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
        <div className="flex items-center justify-between mb-3">
          <div>
            <span className="text-xs font-medium text-red-400 uppercase tracking-wide">
              {snapshot.session_type}
            </span>
            {snapshot.stale && (
              <span className="ml-2 text-xs text-yellow-500 border border-yellow-700 px-1 rounded">
                Stale data
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
              <span>Lap {snapshot.lap}</span>
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

      {/* Driver table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-gray-400 border-b border-gray-700">
              <th className="pb-2 pr-2">Pos</th>
              <th className="pb-2 pr-4">Driver</th>
              <th className="pb-2 text-right">Fantasy Pts</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-800">
            {snapshot.drivers.map((d) => {
              const isUser = userDriverCodes.includes(d.driver_id)
              return (
                <tr key={d.driver_id} className={isUser ? 'bg-red-950/20' : ''}>
                  <td className="py-2 pr-2 text-gray-400 font-mono text-xs">
                    {d.position ?? '-'}
                  </td>
                  <td className="py-2 pr-4">
                    <span className={`font-medium ${isUser ? 'text-red-300' : 'text-white'}`}>
                      {d.name}
                    </span>
                    {d.breakdown.fastest_lap && (
                      <span className="ml-2 text-xs text-purple-400">FL</span>
                    )}
                    {isUser && (
                      <span className="ml-2 text-xs text-red-400">★</span>
                    )}
                  </td>
                  <td className={`py-2 text-right font-bold ${d.fantasy_points >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {d.fantasy_points > 0 ? '+' : ''}{d.fantasy_points}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
