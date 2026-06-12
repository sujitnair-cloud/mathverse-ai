import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useSolver } from '../hooks/useSolver'
import StepDisplay from '../components/StepDisplay'
import ReactMarkdown from 'react-markdown'
import { Calculator, Loader2, AlertCircle, CheckCircle, ChevronDown, ChevronUp, BookOpen, AlertTriangle, Lightbulb } from 'lucide-react'
import type { Difficulty } from '../types'
import clsx from 'clsx'

const DIFFICULTY_OPTIONS: { value: Difficulty; label: string; desc: string }[] = [
  { value: 'kids', label: '🧒 Kids', desc: 'Very simple words' },
  { value: 'basic', label: '📗 Basic', desc: 'Simple English' },
  { value: 'intermediate', label: '📘 Intermediate', desc: 'Standard level' },
  { value: 'advanced', label: '📕 Advanced', desc: 'Technical depth' },
  { value: 'expert', label: '🎓 Expert', desc: 'Graduate level' },
]

const QUICK_EXAMPLES = [
  { cat: 'Algebra', problems: ['Solve: 2x + 3 = 11', 'Solve: x² - 5x + 6 = 0', 'Factor: x² - 9'] },
  { cat: 'Calculus', problems: ['d/dx of x³ + 2x', 'Integrate: 3x²', 'Limit of sin(x)/x as x->0'] },
  { cat: 'Geometry', problems: ['Area of circle radius 5', 'Triangle base=6 height=4', 'Pythagorean a=3 b=4'] },
  { cat: 'Statistics', problems: ['Mean of 2 4 6 8 10', 'Standard deviation 1 2 3 4 5'] },
  { cat: 'Probability', problems: ['C(10, 3)', 'P(5, 2)', 'nCr(8,2)'] },
  { cat: 'Trigonometry', problems: ['sin(30)', 'cos(60)', 'tan(45)'] },
]

export default function Solver() {
  const [searchParams] = useSearchParams()
  const [input, setInput] = useState(searchParams.get('q') || '')
  const [difficulty, setDifficulty] = useState<Difficulty>('intermediate')
  const [showSteps, setShowSteps] = useState(true)
  const [showExplanation, setShowExplanation] = useState(true)
  const { result, loading, error, solve } = useSolver()

  useEffect(() => {
    const q = searchParams.get('q')
    if (q) {
      setInput(q)
      solve(q, difficulty)
    }
  }, []) // eslint-disable-line

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    solve(input, difficulty)
  }

  return (
    <div className="max-w-4xl mx-auto animate-fade-in">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white flex items-center gap-3 mb-2">
          <Calculator className="text-indigo-400" size={32} />
          AI Math Solver
        </h1>
        <p className="text-slate-400">Enter any math problem — equations, calculus, geometry, statistics, and more.</p>
      </div>

      {/* Input form */}
      <form onSubmit={handleSubmit} className="mb-6">
        <div className="bg-slate-800/60 border border-slate-700/50 rounded-2xl p-5">
          <textarea
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); solve(input, difficulty) } }}
            placeholder="Enter a math problem…&#10;Examples: 'Solve x² + 5x + 6 = 0' or 'd/dx of x³' or 'Area of circle radius 5'"
            rows={3}
            className="w-full bg-transparent text-white placeholder-slate-500 resize-none focus:outline-none text-base mb-4"
          />

          {/* Difficulty selector */}
          <div className="flex flex-wrap items-center gap-2 mb-4">
            <span className="text-slate-500 text-xs">Level:</span>
            {DIFFICULTY_OPTIONS.map(opt => (
              <button
                key={opt.value}
                type="button"
                onClick={() => setDifficulty(opt.value)}
                className={clsx(
                  'px-3 py-1 rounded-lg text-xs font-medium transition-all',
                  difficulty === opt.value
                    ? 'bg-indigo-500/30 border border-indigo-500/50 text-indigo-200'
                    : 'bg-slate-700/50 border border-slate-600 text-slate-400 hover:text-white'
                )}
              >
                {opt.label}
              </button>
            ))}
          </div>

          <div className="flex justify-between items-center">
            <span className="text-slate-500 text-xs">Press Enter to solve</span>
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white px-6 py-2.5 rounded-xl font-medium text-sm transition-colors flex items-center gap-2"
            >
              {loading ? <Loader2 size={16} className="animate-spin" /> : <Calculator size={16} />}
              {loading ? 'Solving…' : 'Solve'}
            </button>
          </div>
        </div>
      </form>

      {/* Quick examples */}
      <div className="mb-8">
        <p className="text-slate-500 text-xs mb-3">Quick examples:</p>
        <div className="space-y-2">
          {QUICK_EXAMPLES.map(cat => (
            <div key={cat.cat} className="flex flex-wrap items-center gap-2">
              <span className="text-xs text-slate-500 w-20 flex-shrink-0">{cat.cat}:</span>
              {cat.problems.map(p => (
                <button
                  key={p}
                  onClick={() => { setInput(p); solve(p, difficulty) }}
                  className="text-xs px-2.5 py-1 bg-slate-800 hover:bg-slate-700 border border-slate-700 hover:border-indigo-500/40 text-slate-400 hover:text-indigo-300 rounded-lg font-mono transition-all"
                >
                  {p}
                </button>
              ))}
            </div>
          ))}
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-start gap-3 bg-red-900/20 border border-red-500/30 rounded-xl p-4 mb-6">
          <AlertCircle size={18} className="text-red-400 flex-shrink-0 mt-0.5" />
          <p className="text-red-300 text-sm">{error}</p>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="text-center py-12">
          <div className="inline-flex items-center gap-3 text-indigo-300">
            <Loader2 size={24} className="animate-spin" />
            <span>Solving your problem…</span>
          </div>
        </div>
      )}

      {/* Result */}
      {result && !loading && (
        <div className="space-y-4 animate-slide-up">
          {/* Header */}
          <div className="bg-slate-800/60 border border-slate-700/50 rounded-2xl p-5">
            <div className="flex flex-wrap items-center gap-3 mb-4">
              <CheckCircle size={18} className="text-emerald-400" />
              <span className="text-emerald-300 font-medium">Problem Solved</span>
              <span className="text-xs bg-indigo-500/15 text-indigo-300 px-2 py-0.5 rounded-full border border-indigo-500/20">
                {result.topic.replace(/_/g, ' ')}
              </span>
              <span className="text-xs bg-slate-700 text-slate-400 px-2 py-0.5 rounded-full">
                {result.difficulty}
              </span>
            </div>

            {/* Answer */}
            <div className="bg-indigo-900/30 border border-indigo-500/30 rounded-xl p-4">
              <p className="text-slate-400 text-xs mb-2">Answer</p>
              <p className="text-indigo-200 font-mono text-lg font-semibold break-all">{result.answer}</p>
            </div>

            {result.error && (
              <div className="mt-3 flex items-start gap-2 text-amber-300 text-sm">
                <AlertTriangle size={14} className="flex-shrink-0 mt-0.5" />
                <span>Note: {result.error}</span>
              </div>
            )}
          </div>

          {/* Steps */}
          {result.steps?.length > 0 && (
            <div className="bg-slate-800/60 border border-slate-700/50 rounded-2xl p-5">
              <button
                onClick={() => setShowSteps(s => !s)}
                className="flex items-center justify-between w-full text-left"
              >
                <h3 className="font-semibold text-white flex items-center gap-2">
                  <BookOpen size={16} className="text-indigo-400" />
                  Step-by-Step Solution
                </h3>
                {showSteps ? <ChevronUp size={16} className="text-slate-400" /> : <ChevronDown size={16} className="text-slate-400" />}
              </button>
              {showSteps && (
                <div className="mt-4">
                  <StepDisplay steps={result.steps} />
                </div>
              )}
            </div>
          )}

          {/* AI Explanation */}
          {result.explanation && (
            <div className="bg-slate-800/60 border border-slate-700/50 rounded-2xl p-5">
              <button
                onClick={() => setShowExplanation(s => !s)}
                className="flex items-center justify-between w-full text-left mb-3"
              >
                <h3 className="font-semibold text-white flex items-center gap-2">
                  <Lightbulb size={16} className="text-amber-400" />
                  AI Explanation
                </h3>
                {showExplanation ? <ChevronUp size={16} className="text-slate-400" /> : <ChevronDown size={16} className="text-slate-400" />}
              </button>
              {showExplanation && (
                <div className="prose prose-invert prose-sm max-w-none text-slate-300">
                  <ReactMarkdown>{result.explanation}</ReactMarkdown>
                </div>
              )}
            </div>
          )}

          {/* Formulas & Mistakes */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {result.formulas_used?.length > 0 && (
              <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-4">
                <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
                  📐 Formulas Used
                </h3>
                <ul className="space-y-1.5">
                  {result.formulas_used.map((f, i) => (
                    <li key={i} className="text-xs text-slate-400 flex items-start gap-2">
                      <span className="text-indigo-400 mt-0.5">▸</span>{f}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {result.common_mistakes?.length > 0 && (
              <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-4">
                <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
                  ⚠️ Common Mistakes
                </h3>
                <ul className="space-y-1.5">
                  {result.common_mistakes.map((m, i) => (
                    <li key={i} className="text-xs text-slate-400 flex items-start gap-2">
                      <span className="text-amber-400 mt-0.5">!</span>{m}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Similar problems */}
          {result.similar_problems?.length > 0 && (
            <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-4">
              <h3 className="text-sm font-semibold text-white mb-3">🔁 Similar Practice Problems</h3>
              <div className="flex flex-wrap gap-2">
                {result.similar_problems.map((p, i) => (
                  <button
                    key={i}
                    onClick={() => { setInput(p); solve(p, difficulty) }}
                    className="text-xs px-3 py-1.5 bg-slate-700 hover:bg-indigo-600/30 border border-slate-600 hover:border-indigo-500/50 text-slate-300 rounded-lg font-mono transition-all"
                  >
                    {p}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
