export interface SolveStep {
  step: number
  description: string
  expression: string
}

export interface SolveResult {
  problem: string
  topic: string
  difficulty: string
  steps: SolveStep[]
  answer: string
  latex_answer?: string
  explanation?: string
  alternate_method?: string
  formulas_used: string[]
  common_mistakes: string[]
  similar_problems: string[]
  error?: string
}

export interface Formula {
  id: number
  name: string
  topic: string
  subtopic?: string
  formula: string
  description?: string
  variables?: Record<string, string>
  example?: string
  difficulty: 'basic' | 'intermediate' | 'advanced'
  tags?: string[]
}

export interface MathTopic {
  id: number
  slug: string
  name: string
  category: string
  definition?: string
  explanation?: string
  key_formulas?: string[]
  examples?: { problem: string; solution: string }[]
  use_cases?: string
  difficulty?: string
  related_topics?: string[]
  prerequisites?: string[]
}

export interface QuizQuestion {
  question: string
  options: string[]
  answer?: string
  explanation?: string
}

export interface HistoryItem {
  id: number
  problem: string
  topic: string
  difficulty: string
  answer?: string
  created_at: string
}

export interface UserProfile {
  exists: boolean
  session_id?: string
  username?: string
  user_type?: string
  level?: string
  preferred_language?: string
  dark_mode?: boolean
  topics_explored?: string[]
  total_problems_solved?: number
  streak_days?: number
}

export type Difficulty = 'kids' | 'basic' | 'intermediate' | 'advanced' | 'expert'
export type UserMode = 'kids' | 'student' | 'teacher' | 'professional' | 'exam'
