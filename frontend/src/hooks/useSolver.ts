import { useState, useCallback } from 'react'
import { solveProblem } from '../services/api'
import type { SolveResult, Difficulty } from '../types'

export function useSolver() {
  const [result, setResult] = useState<SolveResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const solve = useCallback(async (problem: string, difficulty: Difficulty = 'intermediate') => {
    if (!problem.trim()) return
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const data = await solveProblem(problem, difficulty)
      setResult(data)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to solve. Is the backend running?'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }, [])

  return { result, loading, error, solve }
}
