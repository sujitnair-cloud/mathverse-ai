import type { Formula } from '../types'
import clsx from 'clsx'

const DIFFICULTY_COLORS = {
  basic: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/20',
  intermediate: 'bg-amber-500/15 text-amber-300 border-amber-500/20',
  advanced: 'bg-red-500/15 text-red-300 border-red-500/20',
}

interface Props {
  formula: Formula
  onClick?: () => void
}

export default function FormulaCard({ formula, onClick }: Props) {
  const dc = DIFFICULTY_COLORS[formula.difficulty] || DIFFICULTY_COLORS.intermediate

  return (
    <div
      onClick={onClick}
      className={clsx(
        'bg-slate-800/60 border border-slate-700/50 rounded-xl p-4 hover:border-indigo-500/40 hover:bg-slate-800 transition-all cursor-pointer group',
        onClick && 'hover:shadow-lg hover:shadow-indigo-500/5'
      )}
    >
      <div className="flex items-start justify-between gap-2 mb-3">
        <h3 className="font-semibold text-white group-hover:text-indigo-300 transition-colors text-sm leading-tight">
          {formula.name}
        </h3>
        <span className={clsx('text-xs px-2 py-0.5 rounded-full border flex-shrink-0', dc)}>
          {formula.difficulty}
        </span>
      </div>

      <div className="bg-slate-900/60 rounded-lg px-3 py-2 mb-3 border border-slate-700/30">
        <code className="text-indigo-200 font-mono text-sm">{formula.formula}</code>
      </div>

      {formula.description && (
        <p className="text-slate-400 text-xs leading-relaxed mb-2">{formula.description}</p>
      )}

      <div className="flex items-center justify-between">
        <span className="text-xs text-indigo-400/70 font-medium">{formula.topic}</span>
        {formula.subtopic && (
          <span className="text-xs text-slate-500">{formula.subtopic}</span>
        )}
      </div>

      {formula.example && (
        <div className="mt-3 pt-3 border-t border-slate-700/30">
          <p className="text-xs text-slate-500 mb-1">Example:</p>
          <p className="text-xs text-slate-400">{formula.example}</p>
        </div>
      )}
    </div>
  )
}
