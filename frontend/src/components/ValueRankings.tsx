import { useState } from 'react'
import type { ValueLeaderboardEntry } from '../lib/types'

interface Props {
  entries: ValueLeaderboardEntry[]
}

type SortKey = 'name' | 'team' | 'price' | 'total_fantasy_pts' | 'xp' | 'value_score'
type SortDir = 'asc' | 'desc'

const COLUMNS: { key: SortKey; label: string; align: 'left' | 'right'; width: string }[] = [
  { key: 'name', label: 'Driver', align: 'left', width: 'w-[30%]' },
  { key: 'team', label: 'Team', align: 'left', width: 'w-[24%]' },
  { key: 'price', label: 'Price', align: 'right', width: 'w-[15%]' },
  { key: 'total_fantasy_pts', label: 'Pts', align: 'right', width: 'w-[12%]' },
  { key: 'xp', label: 'xP', align: 'right', width: 'w-[10%]' },
  { key: 'value_score', label: 'Value', align: 'right', width: 'w-[9%]' },
]

export default function ValueRankings({ entries }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>('value_score')
  const [sortDir, setSortDir] = useState<SortDir>('desc')

  function handleSort(key: SortKey) {
    if (key === sortKey) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      setSortDir(key === 'name' || key === 'team' ? 'asc' : 'desc')
    }
  }

  const sorted = [...entries].sort((a, b) => {
    const av = a[sortKey]
    const bv = b[sortKey]
    const cmp = typeof av === 'string' && typeof bv === 'string'
      ? av.localeCompare(bv)
      : (av as number) - (bv as number)
    return sortDir === 'asc' ? cmp : -cmp
  })

  return (
    <div className="overflow-x-auto -mx-1">
      <table className="w-full text-sm min-w-[480px] px-1 table-fixed">
        <colgroup>
          <col className="w-8" />
          {COLUMNS.map((col) => <col key={col.key} className={col.width} />)}
        </colgroup>
        <thead>
          <tr className="text-left text-gray-400 border-b border-gray-700">
            <th className="pb-2 pr-1 sticky left-0 bg-gray-800 z-10">#</th>
            {COLUMNS.map((col) => (
              <th
                key={col.key}
                onClick={() => handleSort(col.key)}
                className={`pb-2 pr-3 py-3 whitespace-nowrap cursor-pointer select-none hover:text-white transition-colors ${
                  col.align === 'right' ? 'text-right' : ''
                } ${col.key === 'name' ? 'sticky left-8 bg-gray-800 z-10' : ''}`}
              >
                {col.label}
                <span className={`ml-1 text-[10px] ${sortKey === col.key ? 'text-red-400' : 'text-gray-600'}`}>
                  {sortKey === col.key ? (sortDir === 'asc' ? '▲' : '▼') : '▲▼'}
                </span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-800">
          {sorted.map((e, i) => (
            <tr key={e.id} className="hover:bg-gray-700/30">
              <td className="py-2.5 pr-1 text-gray-500 text-xs sticky left-0 bg-gray-800 z-10">{i + 1}</td>
              <td className="py-2.5 pr-3 sticky left-8 bg-gray-800 z-10 whitespace-nowrap overflow-hidden text-ellipsis">
                <span className="font-medium text-white">{e.name}</span>
                <span className="ml-1.5 text-xs text-gray-500 font-mono">{e.code}</span>
              </td>
              <td className="py-2.5 pr-3 text-gray-400 text-xs whitespace-nowrap overflow-hidden text-ellipsis">{e.team}</td>
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
