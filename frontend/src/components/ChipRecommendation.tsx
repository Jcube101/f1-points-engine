import type { ChipRecommendation } from '../lib/types'

interface Props {
  recommendation: ChipRecommendation
}

const confidenceStyle: Record<string, { container: string; badge: string }> = {
  High: {
    container: 'border-green-700 bg-green-900/20',
    badge: 'bg-green-500 text-black',
  },
  Medium: {
    container: 'border-yellow-700 bg-yellow-900/20',
    badge: 'bg-yellow-500 text-black',
  },
  Low: {
    container: 'border-gray-600 bg-gray-800',
    badge: 'bg-gray-500 text-white',
  },
}

export default function ChipRecommendationCard({ recommendation: rec }: Props) {
  const style = confidenceStyle[rec.confidence] ?? confidenceStyle.Low

  return (
    <div className="space-y-4">
      {/* Main recommendation card */}
      <div className={`rounded-xl border-2 p-5 ${style.container}`}>
        {/* Confidence badge — prominent at top */}
        <div className="flex items-start justify-between gap-3 mb-3">
          <h3 className="text-lg font-bold text-white leading-tight">
            {rec.chip === 'Hold' ? 'Hold your chips' : `Use: ${rec.chip}`}
          </h3>
          <span className={`flex-shrink-0 text-sm font-bold px-3 py-1 rounded-full min-h-[32px] flex items-center ${style.badge}`}>
            {rec.confidence}
          </span>
        </div>

        <p className="text-sm text-gray-300 leading-relaxed">{rec.reason}</p>

        {/* "Got it" action button — thumb-friendly */}
        <button
          className="mt-4 w-full min-h-[52px] rounded-xl bg-white/10 hover:bg-white/20 text-white font-semibold text-base transition-colors border border-white/20"
          onClick={() => {/* acknowledged */}}
        >
          {rec.chip === 'Hold' ? 'Got it — holding chips' : `Apply ${rec.chip}`}
        </button>
      </div>

      {/* Alternatives */}
      {rec.alternatives.length > 0 && (
        <div>
          <h4 className="text-sm text-gray-400 font-medium mb-2">Alternatives</h4>
          <div className="space-y-2">
            {rec.alternatives.map((alt) => (
              <div key={alt.chip} className="bg-gray-800 rounded-lg p-3 border border-gray-700">
                <p className="text-sm font-semibold text-white">{alt.chip}</p>
                <p className="text-xs text-gray-400 mt-0.5">{alt.reason}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
