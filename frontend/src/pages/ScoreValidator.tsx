import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchValidation, runValidation } from '../lib/api'

export default function ScoreValidator() {
  const queryClient = useQueryClient()

  const { data: records = [], isLoading } = useQuery({
    queryKey: ['validation'],
    queryFn: fetchValidation,
  })

  const { mutate: triggerValidation, isPending } = useMutation({
    mutationFn: runValidation,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['validation'] }),
  })

  const matched = records.filter((r) => r.delta !== null && r.delta === 0).length
  const discrepancies = records.filter((r) => r.delta !== null && r.delta !== 0).length
  const noOfficial = records.filter((r) => r.official_score === null).length
  const accuracy = records.length > 0 ? (matched / records.length) * 100 : null

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Score Validator</h1>
        <button
          onClick={() => triggerValidation()}
          disabled={isPending}
          className="px-4 py-2 bg-red-600 hover:bg-red-500 text-white text-sm font-medium rounded-lg disabled:opacity-50 transition-colors"
        >
          {isPending ? 'Running...' : 'Run Validation'}
        </button>
      </div>

      <p className="text-gray-400 text-sm">
        Compares our computed fantasy scores against the official F1 Fantasy API.
        Target: 100% match. Discrepancies reveal scoring rule bugs.
      </p>

      {/* Summary stats */}
      {records.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
            <p className="text-xs text-gray-400">Total records</p>
            <p className="text-2xl font-bold text-white mt-1">{records.length}</p>
          </div>
          <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
            <p className="text-xs text-gray-400">Matched</p>
            <p className="text-2xl font-bold text-green-400 mt-1">{matched}</p>
          </div>
          <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
            <p className="text-xs text-gray-400">Discrepancies</p>
            <p className={`text-2xl font-bold mt-1 ${discrepancies > 0 ? 'text-red-400' : 'text-gray-400'}`}>
              {discrepancies}
            </p>
          </div>
          <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
            <p className="text-xs text-gray-400">Accuracy</p>
            <p className={`text-2xl font-bold mt-1 ${accuracy === 100 ? 'text-green-400' : 'text-yellow-400'}`}>
              {accuracy !== null ? `${accuracy.toFixed(0)}%` : '—'}
            </p>
          </div>
        </div>
      )}

      {noOfficial > 0 && (
        <div className="bg-yellow-950/30 border border-yellow-700 rounded-lg p-3 text-sm text-yellow-400">
          {noOfficial} records have no official score (F1 Fantasy API may be offline).
          Our computed scores are stored and will be re-compared when the official API is available.
        </div>
      )}

      {/* Records table */}
      <div className="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
        {isLoading ? (
          <p className="p-6 text-gray-400 text-center">Loading validation records...</p>
        ) : records.length === 0 ? (
          <div className="p-6 text-center">
            <p className="text-gray-400">No validation records yet.</p>
            <p className="text-xs text-gray-600 mt-1">
              Run validation after a race to compare scores.
            </p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-700/50">
              <tr className="text-left text-gray-400">
                <th className="px-4 py-3">Race</th>
                <th className="px-4 py-3">Driver</th>
                <th className="px-4 py-3 text-right">Our Score</th>
                <th className="px-4 py-3 text-right">Official</th>
                <th className="px-4 py-3 text-right">Delta</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700">
              {records.map((r, i) => (
                <tr key={i} className={`hover:bg-gray-700/30 ${r.delta && r.delta !== 0 ? 'bg-red-950/10' : ''}`}>
                  <td className="px-4 py-2 text-gray-300 text-xs">{r.race_name}</td>
                  <td className="px-4 py-2">
                    <span className="text-white">{r.driver_name}</span>
                    <span className="ml-1 text-xs text-gray-500">{r.driver_code}</span>
                  </td>
                  <td className="px-4 py-2 text-right text-white">{r.our_score.toFixed(1)}</td>
                  <td className="px-4 py-2 text-right text-gray-400">
                    {r.official_score !== null ? r.official_score.toFixed(1) : '—'}
                  </td>
                  <td className={`px-4 py-2 text-right font-medium ${
                    r.delta === null ? 'text-gray-600' :
                    r.delta === 0 ? 'text-green-400' : 'text-red-400'
                  }`}>
                    {r.delta !== null ? (r.delta > 0 ? `+${r.delta.toFixed(1)}` : r.delta.toFixed(1)) : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
