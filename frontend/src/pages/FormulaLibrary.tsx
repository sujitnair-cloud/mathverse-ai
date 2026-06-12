import { useState, useEffect } from 'react'
import { searchFormulas, getFormulaTopics } from '../services/api'
import FormulaCard from '../components/FormulaCard'
import type { Formula } from '../types'
import { Library, Search, Loader2, Filter } from 'lucide-react'
import clsx from 'clsx'

const DIFFICULTIES = ['all', 'basic', 'intermediate', 'advanced'] as const

export default function FormulaLibrary() {
  const [formulas, setFormulas] = useState<Formula[]>([])
  const [topics, setTopics] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [query, setQuery] = useState('')
  const [topic, setTopic] = useState('')
  const [difficulty, setDifficulty] = useState<string>('all')
  const [selected, setSelected] = useState<Formula | null>(null)

  useEffect(() => {
    getFormulaTopics().then(setTopics).catch(() => {})
    loadFormulas()
  }, []) // eslint-disable-line

  const loadFormulas = async (q = '', t = '', d = 'all') => {
    setLoading(true)
    try {
      const data = await searchFormulas(q || undefined, t || undefined, d !== 'all' ? d : undefined)
      setFormulas(data)
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    loadFormulas(query, topic, difficulty)
  }

  return (
    <div className="animate-fade-in">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white flex items-center gap-3 mb-2">
          <Library className="text-indigo-400" size={32} />
          Formula Library
        </h1>
        <p className="text-slate-400">Search and browse mathematical formulas across all topics.</p>
      </div>

      {/* Search & Filters */}
      <form onSubmit={handleSearch} className="bg-slate-800/60 border border-slate-700/50 rounded-2xl p-5 mb-6">
        <div className="flex gap-3 mb-4">
          <div className="relative flex-1">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={query}
              onChange={e => setQuery(e.target.value)}
              placeholder="Search formulas…"
              className="w-full pl-9 pr-4 py-2.5 bg-slate-700/50 border border-slate-600 rounded-xl text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm"
            />
          </div>
          <button
            type="submit"
            className="bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2.5 rounded-xl text-sm font-medium transition-colors flex items-center gap-2"
          >
            <Filter size={14} /> Filter
          </button>
        </div>

        <div className="flex flex-wrap gap-3">
          <select
            value={topic}
            onChange={e => { setTopic(e.target.value); loadFormulas(query, e.target.value, difficulty) }}
            className="bg-slate-700/50 border border-slate-600 text-slate-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-indigo-500"
          >
            <option value="">All Topics</option>
            {topics.map(t => <option key={t} value={t}>{t}</option>)}
          </select>

          <div className="flex gap-1">
            {DIFFICULTIES.map(d => (
              <button
                key={d}
                type="button"
                onClick={() => { setDifficulty(d); loadFormulas(query, topic, d) }}
                className={clsx(
                  'px-3 py-1.5 rounded-lg text-xs font-medium transition-all capitalize',
                  difficulty === d
                    ? 'bg-indigo-500/30 border border-indigo-500/50 text-indigo-200'
                    : 'bg-slate-700/50 border border-slate-600 text-slate-400 hover:text-white'
                )}
              >
                {d}
              </button>
            ))}
          </div>
        </div>
      </form>

      {/* Results */}
      {loading ? (
        <div className="text-center py-12 text-indigo-300">
          <Loader2 size={32} className="animate-spin mx-auto mb-3" />
          <p>Loading formulas…</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {formulas.map(f => (
            <FormulaCard key={f.id} formula={f} onClick={() => setSelected(f)} />
          ))}
          {formulas.length === 0 && (
            <div className="col-span-full text-center py-12 text-slate-500">
              No formulas found. Try a different search.
            </div>
          )}
        </div>
      )}

      {/* Modal */}
      {selected && (
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
          onClick={() => setSelected(null)}
        >
          <div
            className="bg-slate-800 border border-slate-700 rounded-2xl p-6 max-w-lg w-full shadow-2xl animate-slide-up"
            onClick={e => e.stopPropagation()}
          >
            <div className="flex items-start justify-between mb-4">
              <h2 className="text-xl font-bold text-white">{selected.name}</h2>
              <button onClick={() => setSelected(null)} className="text-slate-400 hover:text-white text-xl leading-none">&times;</button>
            </div>
            <div className="bg-slate-900 rounded-xl p-4 mb-4 border border-slate-700">
              <code className="text-indigo-200 font-mono text-lg">{selected.formula}</code>
            </div>
            {selected.description && <p className="text-slate-300 text-sm mb-4">{selected.description}</p>}
            {selected.variables && Object.keys(selected.variables).length > 0 && (
              <div className="mb-4">
                <p className="text-slate-500 text-xs mb-2 uppercase tracking-wider">Variables</p>
                <div className="space-y-1">
                  {Object.entries(selected.variables).map(([k, v]) => (
                    <div key={k} className="flex gap-3 text-sm">
                      <code className="text-indigo-300 font-mono w-20 flex-shrink-0">{k}</code>
                      <span className="text-slate-400">{v}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {selected.example && (
              <div className="bg-slate-900/60 rounded-lg p-3 border border-slate-700/50">
                <p className="text-slate-500 text-xs mb-1">Example</p>
                <p className="text-slate-300 text-sm">{selected.example}</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
