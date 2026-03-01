import type { ChipRecommendation } from '../lib/types'

interface Props {
  recommendation: ChipRecommendation
}

const confidenceColor: Record<string, string> = {
  High: 'text-green-400 bg-green-900/30 border-green-700',
  Medium: 'text-yellow-400 bg-yellow-900/30 border-yellow-700',
  Low: 'text-gray-400 bg-gray-800 border-gray-600',
}

export default function ChipRecommendationCard({ recommendation: rec }: Props) {
  const colorClass = confidenceColor[rec.confidence] ?? confidenceColor.Low

  return (
    <div className="space-y-4">
      <div className={`rounded-lg border p-4 ${colorClass}`}>
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-lg font-bold">{rec.chip === 'Hold' ? 'Hold your chips' : `Use: ${rec.chip}`}</h3>
          <span className={`text-xs font-medium px-2 py-0.5 rounded-full border ${colorClass}`}>
            {rec.confidence} confidence
          </span>
        </div>
        <p className="text-sm leading-relaxed">{rec.reason}</p>
      </div>

      {rec.alternatives.length > 0 && (
        <div>
          <h4 className="text-sm text-gray-400 font-medium mb-2">Alternatives</h4>
          <div className="space-y-2">
            {rec.alternatives.map((alt) => (
              <div key={alt.chip} className="bg-gray-800 rounded p-3 border border-gray-700">
                <p className="text-sm font-medium text-white">{alt.chip}</p>
                <p className="text-xs text-gray-400 mt-0.5">{alt.reason}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
