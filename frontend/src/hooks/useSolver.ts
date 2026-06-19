import { useState, useCallback } from 'react'
import axios from 'axios'
import { solveProblem } from '../services/api'
import type { SolveResult, Difficulty } from '../types'

export function useSolver() {
  const [result, setResult] = useState<SolveResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [limitHit, setLimitHit] = useState(false)

  const solve = useCallback(async (problem: string, difficulty: Difficulty = 'intermediate') => {
    if (!problem.trim()) return
    setLoading(true)
    setError(null)
    setResult(null)
    setLimitHit(false)
    try {
      const data = await solveProblem(problem, difficulty)
      setResult(data)
    } catch (err: unknown) {
      if (axios.isAxiosError(err) && err.response?.status === 429) {
        setLimitHit(true)
        setError(err.response.data?.detail || 'Daily limit reached.')
      } else {
        const msg = err instanceof Error ? err.message : 'Failed to solve. Is the backend running?'
        setError(msg)
      }
    } finally {
      setLoading(false)
    }
  }, [])

  return { result, loading, error, limitHit, solve }
}
