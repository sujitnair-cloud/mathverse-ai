import axios from 'axios'
import type { SolveResult, Formula, MathTopic, HistoryItem } from '../types'

const BASE_URL = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/api/v1`
  : '/api/v1'

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
})

// Attach JWT token from localStorage on every request
api.interceptors.request.use(config => {
  const token = localStorage.getItem('mathverse_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// ── Solver ──────────────────────────────────────────────────────────────────
export const solveProblem = async (
  problem: string,
  difficulty = 'intermediate',
  sessionId = getSessionId(),
  includeExplanation = true,
): Promise<SolveResult> => {
  const { data } = await api.post('/solve', {
    problem,
    difficulty,
    session_id: sessionId,
    include_explanation: includeExplanation,
  })
  return data
}

// ── Graph ───────────────────────────────────────────────────────────────────
export const plotFunctions = async (
  expressions: string[],
  xMin = -10,
  xMax = 10,
  title = '',
) => {
  const { data } = await api.post('/graph', { expressions, x_min: xMin, x_max: xMax, title })
  return data
}

export const plot3D = async (expression: string, xMin = -5, xMax = 5, yMin = -5, yMax = 5) => {
  const { data } = await api.post('/graph/3d', { expression, x_min: xMin, x_max: xMax, y_min: yMin, y_max: yMax })
  return data
}

// ── Formulas ─────────────────────────────────────────────────────────────────
export const searchFormulas = async (
  q?: string,
  topic?: string,
  difficulty?: string,
  limit = 20,
  offset = 0,
): Promise<Formula[]> => {
  const { data } = await api.get('/formula/search', { params: { q, topic, difficulty, limit, offset } })
  return data
}

export const getFormulaTopics = async (): Promise<string[]> => {
  const { data } = await api.get('/formula/topics/list')
  return data.topics
}

// ── Topics ───────────────────────────────────────────────────────────────────
export const listTopics = async (category?: string, difficulty?: string): Promise<MathTopic[]> => {
  const { data } = await api.get('/topics', { params: { category, difficulty } })
  return data
}

export const searchTopics = async (q: string): Promise<MathTopic[]> => {
  const { data } = await api.get('/topics/search', { params: { q } })
  return data
}

export const getTopic = async (slug: string): Promise<MathTopic> => {
  const { data } = await api.get(`/topics/${slug}`)
  return data
}

export const getTopicCategories = async (): Promise<string[]> => {
  const { data } = await api.get('/topics/categories')
  return data.categories
}

// ── Quiz ─────────────────────────────────────────────────────────────────────
export const generateQuiz = async (topic: string, difficulty: string, count = 5) => {
  const { data } = await api.post('/quiz/generate', {
    topic,
    difficulty,
    count,
    session_id: getSessionId(),
  })
  return data
}

export const submitQuiz = async (
  topic: string,
  difficulty: string,
  questions: object[],
  userAnswers: string[],
) => {
  const { data } = await api.post('/quiz/submit', {
    session_id: getSessionId(),
    topic,
    difficulty,
    questions,
    user_answers: userAnswers,
  })
  return data
}

// ── History ──────────────────────────────────────────────────────────────────
export const getHistory = async (limit = 50): Promise<{ history: HistoryItem[] }> => {
  const { data } = await api.get('/history', { params: { session_id: getSessionId(), limit } })
  return data
}

export const clearHistory = async () => {
  await api.delete('/history', { params: { session_id: getSessionId() } })
}

// ── User ─────────────────────────────────────────────────────────────────────
export const getUserProfile = async () => {
  const { data } = await api.get('/user/profile', { params: { session_id: getSessionId() } })
  return data
}

export const saveUserProfile = async (profile: object) => {
  const { data } = await api.post('/user/profile', { session_id: getSessionId(), ...profile })
  return data
}

// ── Admin ─────────────────────────────────────────────────────────────────────
export const getAdminDashboard = async () => {
  const { data } = await api.get('/admin/dashboard')
  return data
}

// ── Utilities ────────────────────────────────────────────────────────────────
export function getSessionId(): string {
  let sid = localStorage.getItem('mathverse_session')
  if (!sid) {
    sid = `sess_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`
    localStorage.setItem('mathverse_session', sid)
  }
  return sid
}
