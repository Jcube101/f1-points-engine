import type { ValueLeaderboardEntry } from '../lib/types'

interface Props {
  entries: ValueLeaderboardEntry[]
}

export default function ValueRankings({ entries }: Props) {
  return (
    <div className="overflow-x-auto -mx-1">
      <table className="w-full text-sm min-w-[480px] px-1">
        <thead>
          <tr className="text-left text-gray-400 border-b border-gray-700">
            <th className="pb-2 pr-1 sticky left-0 bg-gray-800 z-10 w-6">#</th>
            <th className="pb-2 pr-3 sticky left-6 bg-gray-800 z-10 whitespace-nowrap">Driver</th>
            <th className="pb-2 pr-3 text-xs whitespace-nowrap">Team</th>
            <th className="pb-2 pr-3 text-right whitespace-nowrap">Price</th>
            <th className="pb-2 pr-3 text-right whitespace-nowrap">Pts</th>
            <th className="pb-2 pr-3 text-right whitespace-nowrap">xP</th>
            <th className="pb-2 text-right whitespace-nowrap">Value</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-800">
          {entries.map((e, i) => (
            <tr key={e.id} className="hover:bg-gray-700/30">
              <td className="py-2.5 pr-1 text-gray-500 text-xs sticky left-0 bg-gray-800 z-10">{i + 1}</td>
              <td className="py-2.5 pr-3 sticky left-6 bg-gray-800 z-10 whitespace-nowrap">
                <span className="font-medium text-white">{e.name}</span>
                <span className="ml-1.5 text-xs text-gray-500 font-mono">{e.code}</span>
              </td>
              <td className="py-2.5 pr-3 text-gray-400 text-xs whitespace-nowrap">{e.team}</td>
              <td className="py-2.5 pr-3 text-right text-green-400 text-xs whitespace-nowrap">
                ${(e.price / 1e6).toFixed(1)}M
              </td>
              <td className={`py-2.5 pr-3 text-right text-xs ${e.total_fantasy_pts >= 0 ? 'text-white' : 'text-red-400'}`}>
                {e.total_fantasy_pts.toFixed(0)}
              </td>
              <td className="py-2.5 pr-3 text-right text-blue-400 text-xs">{e.xp.toFixed(1)}</td>
              <td className={`py-2.5 text-right font-bold text-xs ${
                e.value_score > 1 ? 'text-green-400' : e.value_score > 0 ? 'text-yellow-400' : 'text-red-400'
              }`}>
                {e.value_score.toFixed(2)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
