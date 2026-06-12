import { useState } from 'react'
import { generateQuiz, submitQuiz } from '../services/api'
import type { QuizQuestion } from '../types'
import { Trophy, Loader2, CheckCircle, XCircle, RefreshCw } from 'lucide-react'
import clsx from 'clsx'

const TOPICS = ['algebra', 'calculus', 'statistics', 'geometry', 'trigonometry', 'probability', 'linear-algebra']
const DIFFICULTIES = ['basic', 'intermediate', 'advanced']

export default function Quiz() {
  const [topic, setTopic] = useState('algebra')
  const [difficulty, setDifficulty] = useState('intermediate')
  const [count, setCount] = useState(5)
  const [questions, setQuestions] = useState<QuizQuestion[]>([])
  const [answers, setAnswers] = useState<string[]>([])
  const [result, setResult] = useState<null | { score: number; grade: string; graded_questions: { question: string; user_answer: string; correct_answer: string; explanation: string; is_correct: boolean }[] }>(null)
  const [loading, setLoading] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  const startQuiz = async () => {
    setLoading(true)
    setResult(null)
    setAnswers([])
    try {
      const data = await generateQuiz(topic, difficulty, count)
      setQuestions(data.questions)
    } finally {
      setLoading(false)
    }
  }

  const handleAnswer = (qi: number, ans: string) => {
    setAnswers(prev => {
      const next = [...prev]
      next[qi] = ans
      return next
    })
  }

  const handleSubmit = async () => {
    if (answers.length !== questions.length || answers.some(a => !a)) {
      alert('Please answer all questions.')
      return
    }
    setSubmitting(true)
    try {
      const data = await submitQuiz(topic, difficulty, questions, answers)
      setResult(data)
    } finally {
      setSubmitting(false)
    }
  }

  const GRADE_COLOR: Record<string, string> = {
    A: 'text-emerald-300', B: 'text-blue-300', C: 'text-amber-300', D: 'text-red-300'
  }

  return (
    <div className="max-w-3xl mx-auto animate-fade-in">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white flex items-center gap-3 mb-2">
          <Trophy className="text-amber-400" size={32} />
          Practice Quiz
        </h1>
        <p className="text-slate-400">AI-generated questions to test your mathematics knowledge.</p>
      </div>

      {/* Setup */}
      {!questions.length && !loading && (
        <div className="bg-slate-800/60 border border-slate-700/50 rounded-2xl p-6">
          <h2 className="font-semibold text-white mb-5">Configure Quiz</h2>

          <div className="space-y-5">
            <div>
              <label className="text-slate-400 text-sm mb-2 block">Topic</label>
              <div className="flex flex-wrap gap-2">
                {TOPICS.map(t => (
                  <button key={t} onClick={() => setTopic(t)}
                    className={clsx('px-3 py-1.5 rounded-lg text-sm capitalize transition-all', topic === t ? 'bg-indigo-500/30 border border-indigo-500/50 text-indigo-200' : 'bg-slate-700/50 border border-slate-600 text-slate-400 hover:text-white')}>
                    {t.replace('-', ' ')}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="text-slate-400 text-sm mb-2 block">Difficulty</label>
              <div className="flex gap-2">
                {DIFFICULTIES.map(d => (
                  <button key={d} onClick={() => setDifficulty(d)}
                    className={clsx('px-4 py-1.5 rounded-lg text-sm capitalize transition-all', difficulty === d ? 'bg-indigo-500/30 border border-indigo-500/50 text-indigo-200' : 'bg-slate-700/50 border border-slate-600 text-slate-400 hover:text-white')}>
                    {d}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="text-slate-400 text-sm mb-2 block">Number of Questions: {count}</label>
              <input type="range" min={3} max={10} value={count} onChange={e => setCount(Number(e.target.value))}
                className="w-full accent-indigo-500" />
            </div>

            <button onClick={startQuiz}
              className="w-full bg-indigo-600 hover:bg-indigo-500 text-white py-3 rounded-xl font-semibold transition-colors flex items-center justify-center gap-2">
              <Trophy size={18} /> Start Quiz
            </button>
          </div>
        </div>
      )}

      {loading && (
        <div className="text-center py-12 text-indigo-300">
          <Loader2 size={32} className="animate-spin mx-auto mb-3" />
          <p>Generating {count} questions on {topic}…</p>
        </div>
      )}

      {/* Quiz questions */}
      {questions.length > 0 && !result && (
        <div className="space-y-4">
          <div className="flex items-center justify-between mb-4">
            <p className="text-slate-400 text-sm">{questions.length} questions · {topic} · {difficulty}</p>
            <span className="text-sm text-indigo-300">{answers.filter(Boolean).length}/{questions.length} answered</span>
          </div>

          {questions.map((q, qi) => (
            <div key={qi} className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-5">
              <p className="font-medium text-white mb-4">
                <span className="text-indigo-400 mr-2">Q{qi + 1}.</span>{q.question}
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {q.options?.map((opt, oi) => {
                  const letter = opt.charAt(0)
                  return (
                    <button
                      key={oi}
                      onClick={() => handleAnswer(qi, letter)}
                      className={clsx(
                        'text-left px-4 py-2.5 rounded-lg text-sm transition-all border',
                        answers[qi] === letter
                          ? 'bg-indigo-500/25 border-indigo-500/60 text-indigo-200'
                          : 'bg-slate-700/50 border-slate-600 text-slate-300 hover:border-indigo-500/40 hover:text-white'
                      )}
                    >
                      {opt}
                    </button>
                  )
                })}
              </div>
            </div>
          ))}

          <button
            onClick={handleSubmit}
            disabled={submitting || answers.filter(Boolean).length < questions.length}
            className="w-full bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white py-3 rounded-xl font-semibold transition-colors flex items-center justify-center gap-2"
          >
            {submitting ? <Loader2 size={16} className="animate-spin" /> : <CheckCircle size={16} />}
            Submit Quiz
          </button>
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="space-y-4 animate-slide-up">
          <div className="bg-slate-800/60 border border-slate-700/50 rounded-2xl p-6 text-center">
            <div className={clsx('text-7xl font-bold mb-2', GRADE_COLOR[result.grade] || 'text-white')}>
              {result.grade}
            </div>
            <p className="text-3xl font-bold text-white mb-1">{result.score}%</p>
            <p className="text-slate-400">{result.graded_questions.filter(q => q.is_correct).length} / {result.graded_questions.length} correct</p>

            <button
              onClick={() => { setQuestions([]); setResult(null); setAnswers([]) }}
              className="mt-4 flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-6 py-2.5 rounded-xl font-medium text-sm transition-colors mx-auto"
            >
              <RefreshCw size={14} /> Try Another Quiz
            </button>
          </div>

          {result.graded_questions.map((gq, i) => (
            <div key={i} className={clsx('rounded-xl p-4 border', gq.is_correct ? 'bg-emerald-900/10 border-emerald-500/20' : 'bg-red-900/10 border-red-500/20')}>
              <div className="flex items-start gap-3">
                {gq.is_correct ? <CheckCircle size={16} className="text-emerald-400 flex-shrink-0 mt-0.5" /> : <XCircle size={16} className="text-red-400 flex-shrink-0 mt-0.5" />}
                <div>
                  <p className="text-white text-sm font-medium mb-2">{gq.question}</p>
                  <div className="flex flex-wrap gap-3 text-xs mb-2">
                    <span className={gq.is_correct ? 'text-emerald-300' : 'text-red-300'}>Your answer: {gq.user_answer}</span>
                    {!gq.is_correct && <span className="text-emerald-300">Correct: {gq.correct_answer}</span>}
                  </div>
                  {gq.explanation && <p className="text-slate-400 text-xs">{gq.explanation}</p>}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
