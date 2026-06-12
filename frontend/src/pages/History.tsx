import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { getHistory, clearHistory } from '../services/api'
import type { HistoryItem } from '../types'
import { History as HistoryIcon, Loader2, Trash2, ArrowRight, AlertCircle } from 'lucide-react'

export default function History() {
  const [items, setItems] = useState<HistoryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [clearing, setClearing] = useState(false)
  const navigate = useNavigate()

  useEffect(() => { load() }, [])

  const load = async () => {
    setLoading(true)
    try {
      const data = await getHistory()
      setItems(data.history)
    } finally {
      setLoading(false)
    }
  }

  const handleClear = async () => {
    if (!confirm('Clear all history? This cannot be undone.')) return
    setClearing(true)
    await clearHistory()
    setItems([])
    setClearing(false)
  }

  const formatDate = (s: string) => {
    try { return new Date(s).toLocaleString() } catch { return s }
  }

  return (
    <div className="max-w-3xl mx-auto animate-fade-in">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white flex items-center gap-3 mb-2">
            <HistoryIcon className="text-indigo-400" size={32} />
            Solve History
          </h1>
          <p className="text-slate-400">Your recent math problems and solutions.</p>
        </div>
        {items.length > 0 && (
          <button
            onClick={handleClear}
            disabled={clearing}
            className="flex items-center gap-2 bg-red-900/20 hover:bg-red-900/40 border border-red-500/20 text-red-300 px-4 py-2 rounded-xl text-sm transition-colors"
          >
            <Trash2 size={14} />
            {clearing ? 'Clearing…' : 'Clear All'}
          </button>
        )}
      </div>

      {loading ? (
        <div className="text-center py-12 text-indigo-300">
          <Loader2 size={28} className="animate-spin mx-auto mb-3" />
        </div>
      ) : items.length === 0 ? (
        <div className="text-center py-16">
          <AlertCircle size={40} className="text-slate-600 mx-auto mb-4" />
          <p className="text-slate-500">No history yet.</p>
          <button onClick={() => navigate('/solver')}
            className="mt-4 text-indigo-400 hover:text-indigo-300 text-sm flex items-center gap-1 mx-auto">
            Solve your first problem <ArrowRight size={14} />
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          <p className="text-slate-500 text-sm">{items.length} problems solved</p>
          {items.map(item => (
            <div
              key={item.id}
              onClick={() => navigate(`/solver?q=${encodeURIComponent(item.problem)}`)}
              className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-4 hover:border-indigo-500/40 hover:bg-slate-800 transition-all cursor-pointer group flex items-start justify-between gap-3"
            >
              <div className="min-w-0">
                <p className="text-white font-medium text-sm mb-1 group-hover:text-indigo-300 transition-colors truncate">
                  {item.problem}
                </p>
                <div className="flex flex-wrap gap-2">
                  <span className="text-xs bg-indigo-500/10 text-indigo-300 px-2 py-0.5 rounded-full">
                    {item.topic?.replace(/_/g, ' ')}
                  </span>
                  <span className="text-xs text-slate-500">{formatDate(item.created_at)}</span>
                </div>
                {item.answer && (
                  <code className="mt-2 block text-xs text-emerald-300 font-mono">= {item.answer}</code>
                )}
              </div>
              <ArrowRight size={16} className="text-slate-600 group-hover:text-indigo-400 flex-shrink-0 transition-colors mt-0.5" />
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
