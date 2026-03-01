import { useState } from 'react'
import { optimizeTeam } from '../lib/api'
import type { OptimizedTeam } from '../lib/types'

export function useOptimizer() {
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<{ max_points: OptimizedTeam; best_value: OptimizedTeam } | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function runOptimizer(budget?: number) {
    setLoading(true)
    setError(null)
    try {
      const data = await optimizeTeam(budget)
      setResult(data)
    } catch (err) {
      setError('Optimizer failed — check backend connection')
    } finally {
      setLoading(false)
    }
  }

  return { loading, result, error, runOptimizer }
}
