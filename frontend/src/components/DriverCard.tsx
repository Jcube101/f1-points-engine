import type { Driver } from '../lib/types'

interface Props {
  driver: Driver
  selected?: boolean
  onSelect?: (driver: Driver) => void
  showXP?: boolean
}

export default function DriverCard({ driver, selected, onSelect, showXP = true }: Props) {
  const priceM = (driver.price / 1_000_000).toFixed(1)

  return (
    <div
      onClick={() => onSelect?.(driver)}
      className={`
        relative rounded-lg p-3 border cursor-pointer transition-all
        ${selected
          ? 'border-red-500 bg-red-950/30'
          : 'border-gray-700 bg-gray-800 hover:border-gray-500'
        }
        ${onSelect ? 'cursor-pointer' : ''}
      `}
    >
      {/* Team color bar */}
      <div
        className="absolute top-0 left-0 w-1 h-full rounded-l-lg"
        style={{ backgroundColor: driver.team_color }}
      />
      <div className="pl-2">
        <div className="flex items-center justify-between">
          <div>
            <p className="font-semibold text-sm text-white">{driver.name}</p>
            <p className="text-xs text-gray-400">{driver.team_name}</p>
          </div>
          <div className="text-right">
            <p className="text-sm font-bold text-green-400">${priceM}M</p>
            {showXP && (
              <p className="text-xs text-blue-400">xP: {driver.xp.toFixed(1)}</p>
            )}
          </div>
        </div>
        <div className="mt-2 flex justify-between text-xs text-gray-400">
          <span>Code: <span className="text-white font-mono">{driver.code}</span></span>
          <span>Val: <span className="text-yellow-400">{driver.value_score.toFixed(2)}</span></span>
        </div>
        {selected && (
          <div className="mt-1 text-xs text-red-400 font-medium">Selected</div>
        )}
      </div>
    </div>
  )
}
