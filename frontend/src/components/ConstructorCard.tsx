import type { Constructor } from '../lib/types'

interface Props {
  constructor: Constructor
  selected?: boolean
  onSelect?: (constructor: Constructor) => void
}

export default function ConstructorCard({ constructor: c, selected, onSelect }: Props) {
  const priceM = (c.price / 1_000_000).toFixed(1)

  return (
    <div
      onClick={() => onSelect?.(c)}
      className={`
        relative rounded-lg p-3 border min-h-[64px] transition-all
        ${selected
          ? 'border-red-500 bg-red-950/30'
          : 'border-gray-700 bg-gray-800 hover:border-gray-500'
        }
        ${onSelect ? 'cursor-pointer' : ''}
      `}
    >
      <div
        className="absolute top-0 left-0 w-1 h-full rounded-l-lg"
        style={{ backgroundColor: c.color_hex }}
      />
      <div className="pl-2">
        <div className="flex items-center justify-between">
          <div>
            <p className="font-semibold text-sm text-white">{c.name}</p>
            <p className="text-xs text-gray-400">
              {c.drivers.map((d) => d.code).join(' · ')}
            </p>
          </div>
          <div className="text-right">
            <p className="text-sm font-bold text-green-400">${priceM}M</p>
            <p className="text-xs text-gray-500">Constructor</p>
          </div>
        </div>
        {selected && (
          <div className="mt-1 text-xs text-red-400 font-medium">Selected</div>
        )}
      </div>
    </div>
  )
}
