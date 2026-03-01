import type { FantasyPointsBreakdown } from '../lib/types'

interface Props {
  breakdown: FantasyPointsBreakdown[]
  total: number
}

export default function PointsTable({ breakdown, total }: Props) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-gray-400 border-b border-gray-700">
            <th className="pb-2 pr-4">Driver</th>
            <th className="pb-2 pr-4 text-right">Qualifying</th>
            <th className="pb-2 pr-4 text-right">Race</th>
            <th className="pb-2 pr-4 text-right">Sprint</th>
            <th className="pb-2 text-right font-bold">Total</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-800">
          {breakdown.map((row) => (
            <tr key={row.driver_id}>
              <td className="py-2 pr-4 text-white">{row.driver_name}</td>
              <td className="py-2 pr-4 text-right text-gray-300">{row.qualifying_pts}</td>
              <td className="py-2 pr-4 text-right text-gray-300">{row.race_pts}</td>
              <td className="py-2 pr-4 text-right text-gray-300">{row.sprint_pts}</td>
              <td className={`py-2 text-right font-bold ${row.total >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                {row.total > 0 ? '+' : ''}{row.total}
              </td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr className="border-t border-gray-600">
            <td colSpan={4} className="pt-2 pr-4 text-gray-400 font-medium">Team Total</td>
            <td className={`pt-2 text-right text-lg font-bold ${total >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {total > 0 ? '+' : ''}{total.toFixed(1)}
            </td>
          </tr>
        </tfoot>
      </table>
    </div>
  )
}
