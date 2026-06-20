import { Component, type ReactNode } from 'react'
import { RefreshCw, AlertTriangle } from 'lucide-react'

interface Props { children: ReactNode }
interface State { hasError: boolean; message: string }

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, message: '' }

  static getDerivedStateFromError(error: unknown): State {
    return {
      hasError: true,
      message: error instanceof Error ? error.message : String(error),
    }
  }

  render() {
    if (!this.state.hasError) return this.props.children
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center p-6">
        <div className="max-w-md w-full bg-slate-800/80 border border-red-500/30 rounded-2xl p-8 text-center">
          <div className="w-14 h-14 bg-red-500/15 rounded-full flex items-center justify-center mx-auto mb-4">
            <AlertTriangle size={28} className="text-red-400" />
          </div>
          <h2 className="text-white text-xl font-bold mb-2">Something went wrong</h2>
          <p className="text-slate-400 text-sm mb-2">The page encountered an unexpected error.</p>
          {this.state.message && (
            <p className="text-red-300 text-xs font-mono bg-slate-900 rounded-lg px-3 py-2 mb-5 break-all">
              {this.state.message}
            </p>
          )}
          <button
            onClick={() => window.location.reload()}
            className="inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-5 py-2.5 rounded-xl font-medium text-sm transition-colors"
          >
            <RefreshCw size={15} />
            Reload Page
          </button>
        </div>
      </div>
    )
  }
}
