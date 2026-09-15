import { InlineMath } from 'react-katex'
import 'katex/dist/katex.min.css'
import type { SolveStep } from '../types'

interface Props {
  steps: SolveStep[]
}

export default function StepDisplay({ steps }: Props) {
  if (!steps?.length) return null

  return (
    <div className="space-y-3">
      {steps.map((step) => (
        <div
          key={step.step}
          className="flex gap-3 animate-slide-up"
          style={{ animationDelay: `${step.step * 60}ms` }}
        >
          <div className="flex-shrink-0 w-7 h-7 rounded-full bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center text-indigo-300 text-xs font-bold">
            {step.step}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-slate-300 text-sm">{step.description}</p>
            {step.expression && (
              <div className="mt-1 px-3 py-1.5 bg-slate-800 rounded-lg text-indigo-200 text-sm overflow-x-auto border border-slate-700">
                {step.latex ? (
                  // Falls back to the raw plain-text expression if this
                  // particular LaTeX string fails to parse, rather than
                  // crashing the step list over one malformed step.
                  <InlineMath math={step.latex} renderError={() => <code className="font-mono">{step.expression}</code>} />
                ) : (
                  <code className="font-mono">{step.expression}</code>
                )}
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}
