import { useState, useEffect, useRef } from 'react'
import { plotFunctions, plot3D } from '../services/api'
import { BarChart2, Plus, Trash2, Loader2, AlertCircle } from 'lucide-react'
import clsx from 'clsx'

declare global {
  interface Window { Plotly: { newPlot: (el: HTMLElement, data: unknown[], layout: unknown, config?: unknown) => void } }
}

const PRESET_FUNCTIONS = [
  { label: 'Parabola', expr: 'x**2' },
  { label: 'Sine wave', expr: 'sin(x)' },
  { label: 'Cosine', expr: 'cos(x)' },
  { label: 'Cubic', expr: 'x**3 - 3*x' },
  { label: 'Exponential', expr: 'exp(x)' },
  { label: 'Natural log', expr: 'log(x)' },
  { label: 'tan(x)', expr: 'tan(x)' },
  { label: 'Gaussian', expr: 'exp(-x**2)' },
]

const COLORS = ['#6366f1', '#ec4899', '#10b981', '#f59e0b', '#3b82f6']

export default function GraphCalculator() {
  const [expressions, setExpressions] = useState(['x**2', 'sin(x)'])
  const [xMin, setXMin] = useState(-10)
  const [xMax, setXMax] = useState(10)
  const [title, setTitle] = useState('')
  const [mode, setMode] = useState<'2d' | '3d'>('2d')
  const [expr3d, setExpr3d] = useState('x**2 + y**2')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const plotRef = useRef<HTMLDivElement>(null)
  const plotlyLoaded = useRef(false)

  useEffect(() => {
    // Load Plotly from CDN
    if (!window.Plotly) {
      const script = document.createElement('script')
      script.src = 'https://cdn.plot.ly/plotly-2.32.0.min.js'
      script.onload = () => { plotlyLoaded.current = true; handlePlot() }
      document.head.appendChild(script)
    } else {
      plotlyLoaded.current = true
      handlePlot()
    }
  }, []) // eslint-disable-line

  const handlePlot = async () => {
    if (!window.Plotly || !plotRef.current) return
    setLoading(true)
    setError(null)
    try {
      let graphData
      if (mode === '3d') {
        graphData = await plot3D(expr3d, xMin, xMax, xMin, xMax)
      } else {
        const exprs = expressions.filter(e => e.trim())
        graphData = await plotFunctions(exprs, xMin, xMax, title)
      }
      if (graphData.error) { setError(graphData.error); return }
      window.Plotly.newPlot(plotRef.current, graphData.data, graphData.layout, { responsive: true })
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to plot. Is the backend running?')
    } finally {
      setLoading(false)
    }
  }

  const addExpression = () => setExpressions(e => [...e, ''])
  const removeExpression = (i: number) => setExpressions(e => e.filter((_, idx) => idx !== i))
  const updateExpression = (i: number, val: string) => setExpressions(e => e.map((ex, idx) => idx === i ? val : ex))

  return (
    <div className="animate-fade-in">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-white flex items-center gap-3 mb-2">
          <BarChart2 className="text-indigo-400" size={32} />
          Graphing Calculator
        </h1>
        <p className="text-slate-400">Plot 2D functions and 3D surfaces interactively.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Controls */}
        <div className="space-y-4">
          {/* Mode toggle */}
          <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-4">
            <div className="flex gap-2 mb-4">
              {(['2d', '3d'] as const).map(m => (
                <button
                  key={m}
                  onClick={() => setMode(m)}
                  className={clsx('flex-1 py-2 rounded-lg text-sm font-medium transition-all', mode === m ? 'bg-indigo-600 text-white' : 'bg-slate-700 text-slate-400 hover:text-white')}
                >
                  {m.toUpperCase()} Plot
                </button>
              ))}
            </div>

            {mode === '2d' ? (
              <div className="space-y-3">
                <p className="text-slate-400 text-xs font-medium uppercase tracking-wider">Functions</p>
                {expressions.map((expr, i) => (
                  <div key={i} className="flex gap-2 items-center">
                    <div className="w-3 h-3 rounded-full flex-shrink-0" style={{ backgroundColor: COLORS[i % COLORS.length] }} />
                    <input
                      value={expr}
                      onChange={e => updateExpression(i, e.target.value)}
                      onKeyDown={e => e.key === 'Enter' && handlePlot()}
                      placeholder={`f(x) = ${i === 0 ? 'x**2' : 'sin(x)'}`}
                      className="flex-1 bg-slate-700/50 border border-slate-600 rounded-lg px-3 py-1.5 text-white text-sm font-mono focus:outline-none focus:ring-1 focus:ring-indigo-500"
                    />
                    <button onClick={() => removeExpression(i)} className="text-slate-500 hover:text-red-400 transition-colors">
                      <Trash2 size={14} />
                    </button>
                  </div>
                ))}
                <button onClick={addExpression} className="flex items-center gap-1 text-indigo-400 hover:text-indigo-300 text-xs transition-colors">
                  <Plus size={12} /> Add function
                </button>
              </div>
            ) : (
              <div>
                <p className="text-slate-400 text-xs font-medium uppercase tracking-wider mb-2">f(x, y) =</p>
                <input
                  value={expr3d}
                  onChange={e => setExpr3d(e.target.value)}
                  className="w-full bg-slate-700/50 border border-slate-600 rounded-lg px-3 py-2 text-white font-mono text-sm focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
              </div>
            )}
          </div>

          {/* Range & Title */}
          <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-4 space-y-3">
            <p className="text-slate-400 text-xs font-medium uppercase tracking-wider">Settings</p>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-slate-500 text-xs">x min</label>
                <input type="number" value={xMin} onChange={e => setXMin(Number(e.target.value))}
                  className="w-full bg-slate-700/50 border border-slate-600 rounded-lg px-2 py-1.5 text-white text-sm focus:outline-none focus:ring-1 focus:ring-indigo-500" />
              </div>
              <div>
                <label className="text-slate-500 text-xs">x max</label>
                <input type="number" value={xMax} onChange={e => setXMax(Number(e.target.value))}
                  className="w-full bg-slate-700/50 border border-slate-600 rounded-lg px-2 py-1.5 text-white text-sm focus:outline-none focus:ring-1 focus:ring-indigo-500" />
              </div>
            </div>
            <input
              value={title}
              onChange={e => setTitle(e.target.value)}
              placeholder="Chart title (optional)"
              className="w-full bg-slate-700/50 border border-slate-600 rounded-lg px-3 py-1.5 text-white text-sm placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
          </div>

          {/* Presets */}
          {mode === '2d' && (
            <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-4">
              <p className="text-slate-400 text-xs font-medium uppercase tracking-wider mb-3">Preset Functions</p>
              <div className="grid grid-cols-2 gap-1.5">
                {PRESET_FUNCTIONS.map(p => (
                  <button
                    key={p.expr}
                    onClick={() => { setExpressions([p.expr]); setTimeout(handlePlot, 100) }}
                    className="text-xs px-2 py-1.5 bg-slate-700/50 hover:bg-indigo-500/20 border border-slate-600 hover:border-indigo-500/40 text-slate-300 rounded-lg font-mono transition-all text-left"
                  >
                    {p.label}
                  </button>
                ))}
              </div>
            </div>
          )}

          <button
            onClick={handlePlot}
            disabled={loading}
            className="w-full bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white py-3 rounded-xl font-medium transition-colors flex items-center justify-center gap-2"
          >
            {loading ? <Loader2 size={16} className="animate-spin" /> : <BarChart2 size={16} />}
            Plot Graph
          </button>
        </div>

        {/* Graph */}
        <div className="lg:col-span-2">
          {error && (
            <div className="flex items-center gap-2 bg-red-900/20 border border-red-500/30 rounded-xl p-3 mb-4 text-red-300 text-sm">
              <AlertCircle size={16} />
              {error}
            </div>
          )}
          <div
            ref={plotRef}
            className="bg-slate-800/60 border border-slate-700/50 rounded-2xl overflow-hidden min-h-96"
            style={{ minHeight: '450px' }}
          >
            {!loading && (
              <div className="flex items-center justify-center h-96 text-slate-500 text-sm">
                {window.Plotly ? 'Configure and click "Plot Graph"' : 'Loading Plotly…'}
              </div>
            )}
          </div>
          <p className="text-slate-600 text-xs mt-2 text-center">
            Use Python/NumPy syntax: x**2, sin(x), exp(x), log(x), sqrt(x), pi
          </p>
        </div>
      </div>
    </div>
  )
}
