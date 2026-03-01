import type { Driver, Constructor } from '../lib/types'

interface Props {
  drivers: Driver[]
  constructors: Constructor[]
  budget?: number
  drsBoostDriverId?: number | null
  onRemoveDriver?: (id: number) => void
  onRemoveConstructor?: (id: number) => void
  onSetDrs?: (id: number) => void
}

const BUDGET = 100_000_000

export default function TeamSummary({
  drivers,
  constructors,
  budget = BUDGET,
  drsBoostDriverId,
  onRemoveDriver,
  onRemoveConstructor,
  onSetDrs,
}: Props) {
  const spent = drivers.reduce((s, d) => s + d.price, 0) + constructors.reduce((s, c) => s + c.price, 0)
  const remaining = budget - spent
  const pct = Math.min(100, (spent / budget) * 100)

  return (
    <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
      <h3 className="font-bold text-white mb-3">My Team</h3>

      {/* Budget bar */}
      <div className="mb-4">
        <div className="flex justify-between text-xs text-gray-400 mb-1">
          <span>Budget used: ${(spent / 1e6).toFixed(1)}M</span>
          <span className={remaining < 0 ? 'text-red-400' : 'text-green-400'}>
            ${(remaining / 1e6).toFixed(1)}M remaining
          </span>
        </div>
        <div className="w-full bg-gray-700 rounded-full h-2">
          <div
            className={`h-2 rounded-full transition-all ${pct >= 100 ? 'bg-red-500' : 'bg-green-500'}`}
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>

      {/* Drivers */}
      <div className="mb-3">
        <p className="text-xs text-gray-500 uppercase tracking-wide mb-2">
          Drivers ({drivers.length}/5)
        </p>
        {drivers.length === 0 ? (
          <p className="text-xs text-gray-600">No drivers selected</p>
        ) : (
          <div className="space-y-1.5">
            {drivers.map((d) => (
              <div key={d.id} className="flex items-center justify-between bg-gray-700/50 rounded px-2 py-1">
                <div className="flex items-center gap-2">
                  <div className="w-1 h-4 rounded" style={{ backgroundColor: d.team_color }} />
                  <span className="text-sm text-white">{d.name}</span>
                  {drsBoostDriverId === d.id && (
                    <span className="text-xs bg-yellow-600 text-black px-1 rounded">DRS</span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-green-400">${(d.price / 1e6).toFixed(1)}M</span>
                  {onSetDrs && (
                    <button
                      onClick={() => onSetDrs(d.id)}
                      className="text-xs text-yellow-500 hover:text-yellow-300"
                      title="Set DRS Boost"
                    >
                      DRS
                    </button>
                  )}
                  {onRemoveDriver && (
                    <button
                      onClick={() => onRemoveDriver(d.id)}
                      className="text-xs text-gray-500 hover:text-red-400"
                    >
                      ✕
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Constructors */}
      <div>
        <p className="text-xs text-gray-500 uppercase tracking-wide mb-2">
          Constructors ({constructors.length}/2)
        </p>
        {constructors.length === 0 ? (
          <p className="text-xs text-gray-600">No constructors selected</p>
        ) : (
          <div className="space-y-1.5">
            {constructors.map((c) => (
              <div key={c.id} className="flex items-center justify-between bg-gray-700/50 rounded px-2 py-1">
                <div className="flex items-center gap-2">
                  <div className="w-1 h-4 rounded" style={{ backgroundColor: c.color_hex }} />
                  <span className="text-sm text-white">{c.name}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-green-400">${(c.price / 1e6).toFixed(1)}M</span>
                  {onRemoveConstructor && (
                    <button
                      onClick={() => onRemoveConstructor(c.id)}
                      className="text-xs text-gray-500 hover:text-red-400"
                    >
                      ✕
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Valid team indicator */}
      {drivers.length === 5 && constructors.length === 2 && remaining >= 0 && (
        <div className="mt-3 text-center text-xs text-green-400 font-medium">
          Valid team!
        </div>
      )}
    </div>
  )
}
