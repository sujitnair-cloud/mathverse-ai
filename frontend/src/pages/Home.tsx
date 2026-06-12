import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, Calculator, BookOpen, Library, BarChart2, Trophy, Zap, Star, ArrowRight } from 'lucide-react'

const TOPIC_CARDS = [
  { emoji: '➕', label: 'Arithmetic', desc: 'Numbers, operations, fractions', level: 'Kids & Beginners', to: '/topics?cat=Foundation', color: 'from-emerald-500/20 to-teal-500/20 border-emerald-500/30' },
  { emoji: '𝑥', label: 'Algebra', desc: 'Equations, polynomials, functions', level: 'School', to: '/topics?cat=Foundation', color: 'from-blue-500/20 to-indigo-500/20 border-blue-500/30' },
  { emoji: '△', label: 'Geometry', desc: 'Shapes, area, volume, coordinates', level: 'School', to: '/topics?cat=Foundation', color: 'from-violet-500/20 to-purple-500/20 border-violet-500/30' },
  { emoji: 'sin', label: 'Trigonometry', desc: 'Angles, triangles, waves', level: 'Intermediate', to: '/topics?cat=Intermediate', color: 'from-pink-500/20 to-rose-500/20 border-pink-500/30' },
  { emoji: '∫', label: 'Calculus', desc: 'Derivatives, integrals, limits', level: 'Advanced', to: '/topics?cat=Advanced', color: 'from-orange-500/20 to-amber-500/20 border-orange-500/30' },
  { emoji: 'σ', label: 'Statistics', desc: 'Data, probability, distributions', level: 'Intermediate', to: '/topics?cat=Intermediate', color: 'from-cyan-500/20 to-sky-500/20 border-cyan-500/30' },
  { emoji: '∑', label: 'Linear Algebra', desc: 'Matrices, vectors, transformations', level: 'Advanced', to: '/topics?cat=Advanced', color: 'from-indigo-500/20 to-blue-500/20 border-indigo-500/30' },
  { emoji: '💰', label: 'Finance Math', desc: 'Interest, investment, EMI', level: 'Applied', to: '/topics?cat=Applied', color: 'from-yellow-500/20 to-amber-500/20 border-yellow-500/30' },
]

const FEATURES = [
  { icon: Calculator, title: 'AI Solver', desc: 'Step-by-step solutions for any math problem', href: '/solver' },
  { icon: Library, title: 'Formula Library', desc: '100+ formulas across all math topics', href: '/formulas' },
  { icon: BarChart2, title: 'Graphing Calculator', desc: 'Interactive 2D and 3D function plots', href: '/graph' },
  { icon: Trophy, title: 'Practice Quizzes', desc: 'Test yourself with AI-generated problems', href: '/quiz' },
]

const EXAMPLE_PROBLEMS = [
  'Solve: x² + 5x + 6 = 0',
  'Integrate: x³ + 2x',
  'd/dx of sin(x²)',
  'Area of circle radius 7',
  'Mean of [2, 4, 6, 8, 10]',
  'C(10, 3)',
  'det([[1,2],[3,4]])',
  'sin(45°)',
]

export default function Home() {
  const navigate = useNavigate()
  const [query, setQuery] = useState('')

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (query.trim()) {
      navigate(`/solver?q=${encodeURIComponent(query)}`)
    }
  }

  return (
    <div className="animate-fade-in">
      {/* Hero */}
      <section className="text-center py-16 md:py-24">
        <div className="inline-flex items-center gap-2 bg-indigo-500/10 border border-indigo-500/20 rounded-full px-4 py-1.5 text-indigo-300 text-sm mb-6">
          <Zap size={14} className="text-indigo-400" />
          AI-Powered Mathematics Platform
        </div>
        <h1 className="text-4xl md:text-6xl font-extrabold text-white mb-4 leading-tight">
          Mathematics Made{' '}
          <span className="bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
            Simple & Powerful
          </span>
        </h1>
        <p className="text-slate-400 text-lg md:text-xl max-w-2xl mx-auto mb-10">
          From basic arithmetic to advanced calculus — solve, learn, visualise, and master mathematics with AI-powered step-by-step explanations.
        </p>

        {/* Search bar */}
        <form onSubmit={handleSearch} className="max-w-2xl mx-auto">
          <div className="relative">
            <Search size={20} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={query}
              onChange={e => setQuery(e.target.value)}
              placeholder="Ask any math question… e.g. 'Solve x² + 5x + 6 = 0'"
              className="w-full pl-12 pr-28 py-4 bg-slate-800 border border-slate-600 rounded-2xl text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent text-base shadow-xl"
            />
            <button
              type="submit"
              className="absolute right-2 top-1/2 -translate-y-1/2 bg-indigo-600 hover:bg-indigo-500 text-white px-5 py-2 rounded-xl font-medium text-sm transition-colors flex items-center gap-1.5"
            >
              Solve <ArrowRight size={14} />
            </button>
          </div>
        </form>

        {/* Example chips */}
        <div className="mt-4 flex flex-wrap justify-center gap-2">
          {EXAMPLE_PROBLEMS.map(p => (
            <button
              key={p}
              onClick={() => navigate(`/solver?q=${encodeURIComponent(p)}`)}
              className="px-3 py-1.5 text-xs bg-slate-800 hover:bg-slate-700 border border-slate-700 hover:border-indigo-500/50 text-slate-300 rounded-lg transition-all font-mono"
            >
              {p}
            </button>
          ))}
        </div>
      </section>

      {/* Features */}
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-16">
        {FEATURES.map(({ icon: Icon, title, desc, href }) => (
          <a
            key={href}
            href={href}
            className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-5 hover:border-indigo-500/40 hover:bg-slate-800 transition-all group"
          >
            <div className="w-10 h-10 rounded-xl bg-indigo-500/15 flex items-center justify-center mb-3 group-hover:bg-indigo-500/25 transition-colors">
              <Icon size={20} className="text-indigo-400" />
            </div>
            <h3 className="font-semibold text-white mb-1 group-hover:text-indigo-300 transition-colors">{title}</h3>
            <p className="text-slate-400 text-sm">{desc}</p>
          </a>
        ))}
      </section>

      {/* Topic cards */}
      <section className="mb-16">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-white">Browse by Topic</h2>
          <a href="/topics" className="text-indigo-400 hover:text-indigo-300 text-sm flex items-center gap-1">
            All topics <ArrowRight size={14} />
          </a>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {TOPIC_CARDS.map(card => (
            <a
              key={card.label}
              href={card.to}
              className={`bg-gradient-to-br ${card.color} border rounded-xl p-5 hover:scale-[1.02] transition-all group`}
            >
              <div className="text-3xl mb-3 font-mono">{card.emoji}</div>
              <h3 className="font-bold text-white mb-1 group-hover:text-indigo-200">{card.label}</h3>
              <p className="text-slate-400 text-xs mb-3">{card.desc}</p>
              <span className="text-xs bg-slate-900/40 text-slate-300 px-2 py-1 rounded-full">{card.level}</span>
            </a>
          ))}
        </div>
      </section>

      {/* User modes */}
      <section className="bg-gradient-to-r from-indigo-900/30 to-purple-900/30 border border-indigo-500/20 rounded-2xl p-8 text-center">
        <Star size={24} className="text-indigo-400 mx-auto mb-3" />
        <h2 className="text-2xl font-bold text-white mb-2">Built for Everyone</h2>
        <p className="text-slate-400 mb-6 max-w-xl mx-auto">
          Whether you're 8 or 80, a student or a scientist — MathVerse AI adapts explanations to your level.
        </p>
        <div className="flex flex-wrap justify-center gap-3">
          {['Kids Mode 🧒', 'Student Mode 📚', 'Exam Mode 🎯', 'Teacher Mode 👩‍🏫', 'Engineer Mode ⚙️', 'Finance Mode 📈'].map(m => (
            <span key={m} className="px-4 py-2 bg-slate-800 border border-slate-700 rounded-xl text-slate-300 text-sm hover:border-indigo-500/50 transition-colors cursor-pointer">
              {m}
            </span>
          ))}
        </div>
      </section>
    </div>
  )
}
