import { useState, useEffect } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { listTopics, searchTopics, getTopic, getTopicCategories } from '../services/api'
import type { MathTopic } from '../types'
import { BookOpen, Search, Loader2, ArrowLeft, ChevronRight } from 'lucide-react'
import clsx from 'clsx'

const DIFFICULTY_COLOR: Record<string, string> = {
  basic: 'text-emerald-300 bg-emerald-500/10 border-emerald-500/20',
  intermediate: 'text-amber-300 bg-amber-500/10 border-amber-500/20',
  advanced: 'text-red-300 bg-red-500/10 border-red-500/20',
}

export default function TopicWiki() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const [topics, setTopics] = useState<MathTopic[]>([])
  const [categories, setCategories] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState(searchParams.get('cat') || '')
  const [selected, setSelected] = useState<MathTopic | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)

  useEffect(() => {
    getTopicCategories().then(setCategories).catch(() => {})
    loadTopics()
  }, []) // eslint-disable-line

  useEffect(() => {
    loadTopics()
  }, [category]) // eslint-disable-line

  const loadTopics = async () => {
    setLoading(true)
    try {
      const data = await listTopics(category || undefined)
      setTopics(data)
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim()) { loadTopics(); return }
    setLoading(true)
    try {
      const data = await searchTopics(query)
      setTopics(data)
    } finally {
      setLoading(false)
    }
  }

  const openTopic = async (slug: string) => {
    setDetailLoading(true)
    try {
      const data = await getTopic(slug)
      setSelected(data)
    } finally {
      setDetailLoading(false)
    }
  }

  if (selected) {
    return (
      <div className="max-w-3xl mx-auto animate-fade-in">
        <button
          onClick={() => setSelected(null)}
          className="flex items-center gap-2 text-slate-400 hover:text-white mb-6 transition-colors"
        >
          <ArrowLeft size={16} /> Back to Topics
        </button>

        <div className="bg-slate-800/60 border border-slate-700/50 rounded-2xl p-6 md:p-8">
          <div className="flex items-start justify-between mb-2">
            <span className="text-xs text-indigo-400 font-medium uppercase tracking-wider">{selected.category}</span>
            {selected.difficulty && (
              <span className={clsx('text-xs px-2 py-0.5 rounded-full border', DIFFICULTY_COLOR[selected.difficulty] || DIFFICULTY_COLOR.basic)}>
                {selected.difficulty}
              </span>
            )}
          </div>
          <h1 className="text-3xl font-bold text-white mb-4">{selected.name}</h1>

          {selected.definition && (
            <div className="bg-indigo-900/20 border border-indigo-500/20 rounded-xl p-4 mb-6">
              <p className="text-indigo-200 text-sm leading-relaxed font-medium">{selected.definition}</p>
            </div>
          )}

          {selected.explanation && (
            <div className="mb-6">
              <h2 className="text-lg font-semibold text-white mb-3">Explanation</h2>
              <p className="text-slate-300 text-sm leading-relaxed">{selected.explanation}</p>
            </div>
          )}

          {selected.key_formulas && selected.key_formulas.length > 0 && (
            <div className="mb-6">
              <h2 className="text-lg font-semibold text-white mb-3">Key Formulas</h2>
              <ul className="space-y-2">
                {selected.key_formulas.map((f, i) => (
                  <li key={i} className="flex items-center gap-3 bg-slate-900/60 rounded-lg px-4 py-2.5 border border-slate-700/40">
                    <span className="text-indigo-400 flex-shrink-0">▸</span>
                    <code className="text-indigo-200 font-mono text-sm">{f}</code>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {selected.examples && selected.examples.length > 0 && (
            <div className="mb-6">
              <h2 className="text-lg font-semibold text-white mb-3">Examples</h2>
              <div className="space-y-3">
                {selected.examples.map((ex, i) => (
                  <div key={i} className="bg-slate-900/40 rounded-xl p-4 border border-slate-700/30">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <p className="text-slate-400 text-xs mb-1">Problem</p>
                        <code className="text-white text-sm font-mono">{ex.problem}</code>
                      </div>
                      <ChevronRight size={16} className="text-slate-600 flex-shrink-0 mt-4" />
                      <div>
                        <p className="text-slate-400 text-xs mb-1">Solution</p>
                        <code className="text-emerald-300 text-sm font-mono">{ex.solution}</code>
                      </div>
                    </div>
                    <button
                      onClick={() => navigate(`/solver?q=${encodeURIComponent(ex.problem)}`)}
                      className="mt-3 text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
                    >
                      Try in solver →
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {selected.use_cases && (
            <div className="mb-6">
              <h2 className="text-lg font-semibold text-white mb-2">Real-world Uses</h2>
              <p className="text-slate-400 text-sm">{selected.use_cases}</p>
            </div>
          )}

          {selected.prerequisites && selected.prerequisites.length > 0 && (
            <div className="mb-4">
              <h2 className="text-sm font-semibold text-slate-400 mb-2">Prerequisites</h2>
              <div className="flex flex-wrap gap-2">
                {selected.prerequisites.map(p => (
                  <button key={p} onClick={() => openTopic(p)}
                    className="px-3 py-1 bg-slate-700 hover:bg-indigo-600/20 border border-slate-600 text-slate-300 text-xs rounded-full transition-all">
                    {p}
                  </button>
                ))}
              </div>
            </div>
          )}

          {selected.related_topics && selected.related_topics.length > 0 && (
            <div>
              <h2 className="text-sm font-semibold text-slate-400 mb-2">Related Topics</h2>
              <div className="flex flex-wrap gap-2">
                {selected.related_topics.map(r => (
                  <button key={r} onClick={() => openTopic(r)}
                    className="px-3 py-1 bg-indigo-500/10 hover:bg-indigo-500/20 border border-indigo-500/20 text-indigo-300 text-xs rounded-full transition-all">
                    {r}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="animate-fade-in">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white flex items-center gap-3 mb-2">
          <BookOpen className="text-indigo-400" size={32} />
          Math Topics
        </h1>
        <p className="text-slate-400">Explore mathematics like a Wikipedia — definitions, formulas, and examples.</p>
      </div>

      {/* Search */}
      <form onSubmit={handleSearch} className="flex gap-3 mb-6">
        <div className="relative flex-1">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Search topics…"
            className="w-full pl-9 pr-4 py-2.5 bg-slate-800 border border-slate-700 rounded-xl text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm"
          />
        </div>
        <button type="submit" className="bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2.5 rounded-xl text-sm font-medium transition-colors">
          Search
        </button>
      </form>

      {/* Category filter */}
      <div className="flex flex-wrap gap-2 mb-6">
        <button
          onClick={() => setCategory('')}
          className={clsx('px-3 py-1.5 rounded-lg text-xs font-medium transition-all', !category ? 'bg-indigo-500/30 border border-indigo-500/50 text-indigo-200' : 'bg-slate-700/50 border border-slate-600 text-slate-400 hover:text-white')}
        >
          All
        </button>
        {categories.map(c => (
          <button
            key={c}
            onClick={() => setCategory(c)}
            className={clsx('px-3 py-1.5 rounded-lg text-xs font-medium transition-all', category === c ? 'bg-indigo-500/30 border border-indigo-500/50 text-indigo-200' : 'bg-slate-700/50 border border-slate-600 text-slate-400 hover:text-white')}
          >
            {c}
          </button>
        ))}
      </div>

      {detailLoading && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center">
          <Loader2 size={32} className="text-indigo-400 animate-spin" />
        </div>
      )}

      {loading ? (
        <div className="text-center py-12 text-indigo-300">
          <Loader2 size={32} className="animate-spin mx-auto mb-3" />
          <p>Loading topics…</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {topics.map(t => (
            <div
              key={t.id}
              onClick={() => openTopic(t.slug)}
              className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-5 hover:border-indigo-500/40 hover:bg-slate-800 transition-all cursor-pointer group"
            >
              <div className="flex items-start justify-between mb-2">
                <span className="text-xs text-indigo-400/70">{t.category}</span>
                {t.difficulty && (
                  <span className={clsx('text-xs px-2 py-0.5 rounded-full border', DIFFICULTY_COLOR[t.difficulty] || DIFFICULTY_COLOR.basic)}>
                    {t.difficulty}
                  </span>
                )}
              </div>
              <h3 className="font-bold text-white group-hover:text-indigo-300 transition-colors mb-2">{t.name}</h3>
              {t.definition && (
                <p className="text-slate-400 text-xs leading-relaxed line-clamp-3">{t.definition}</p>
              )}
              {t.key_formulas && t.key_formulas.length > 0 && (
                <code className="mt-3 block text-xs text-indigo-300/70 font-mono truncate">
                  {t.key_formulas[0]}
                </code>
              )}
            </div>
          ))}
          {topics.length === 0 && (
            <div className="col-span-full text-center py-12 text-slate-500">No topics found.</div>
          )}
        </div>
      )}
    </div>
  )
}
