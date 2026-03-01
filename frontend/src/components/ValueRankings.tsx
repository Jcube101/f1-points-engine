import type { ValueLeaderboardEntry } from '../lib/types'

interface Props {
  entries: ValueLeaderboardEntry[]
}

export default function ValueRankings({ entries }: Props) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-gray-400 border-b border-gray-700">
            <th className="pb-2 pr-2">#</th>
            <th className="pb-2 pr-4">Driver</th>
            <th className="pb-2 pr-4">Team</th>
            <th className="pb-2 pr-4 text-right">Price</th>
            <th className="pb-2 pr-4 text-right">Total Pts</th>
            <th className="pb-2 pr-4 text-right">xP</th>
            <th className="pb-2 text-right">Value</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-800">
          {entries.map((e, i) => (
            <tr key={e.id} className="hover:bg-gray-800/50">
              <td className="py-2 pr-2 text-gray-500 text-xs">{i + 1}</td>
              <td className="py-2 pr-4">
                <span className="font-medium text-white">{e.name}</span>
                <span className="ml-2 text-xs text-gray-500 font-mono">{e.code}</span>
              </td>
              <td className="py-2 pr-4 text-gray-400 text-xs">{e.team}</td>
              <td className="py-2 pr-4 text-right text-green-400">${(e.price / 1e6).toFixed(1)}M</td>
              <td className={`py-2 pr-4 text-right ${e.total_fantasy_pts >= 0 ? 'text-white' : 'text-red-400'}`}>
                {e.total_fantasy_pts.toFixed(0)}
              </td>
              <td className="py-2 pr-4 text-right text-blue-400">{e.xp.toFixed(1)}</td>
              <td className={`py-2 text-right font-bold ${e.value_score > 1 ? 'text-green-400' : e.value_score > 0 ? 'text-yellow-400' : 'text-red-400'}`}>
                {e.value_score.toFixed(2)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
