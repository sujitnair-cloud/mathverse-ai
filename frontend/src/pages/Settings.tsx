import { useTheme } from '../hooks/useTheme'
import { Settings as SettingsIcon, Sun, Moon, Zap } from 'lucide-react'
import clsx from 'clsx'

export default function Settings() {
  const { isDark, toggle } = useTheme()

  return (
    <div className="max-w-2xl mx-auto animate-fade-in">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white flex items-center gap-3 mb-2">
          <SettingsIcon className="text-indigo-400" size={32} />
          Settings
        </h1>
      </div>

      <div className="space-y-4">
        <div className="bg-slate-800/60 border border-slate-700/50 rounded-2xl p-6">
          <h2 className="font-semibold text-white mb-4">Appearance</h2>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {isDark ? <Moon size={18} className="text-indigo-400" /> : <Sun size={18} className="text-amber-400" />}
              <div>
                <p className="text-white text-sm font-medium">Theme</p>
                <p className="text-slate-400 text-xs">{isDark ? 'Dark mode' : 'Light mode'}</p>
              </div>
            </div>
            <button onClick={toggle}
              className={clsx('relative w-12 h-6 rounded-full transition-colors', isDark ? 'bg-indigo-600' : 'bg-slate-600')}>
              <span className={clsx('absolute top-1 w-4 h-4 rounded-full bg-white transition-transform', isDark ? 'translate-x-7' : 'translate-x-1')} />
            </button>
          </div>
        </div>

        <div className="bg-slate-800/60 border border-slate-700/50 rounded-2xl p-6">
          <h2 className="font-semibold text-white mb-4 flex items-center gap-2">
            <Zap size={16} className="text-amber-400" /> AI Provider
          </h2>
          <p className="text-slate-400 text-sm mb-3">Configure your AI provider in the backend <code className="text-indigo-300">.env</code> file.</p>
          <div className="grid grid-cols-3 gap-2">
            {['Anthropic Claude', 'OpenAI GPT-4', 'Google Gemini'].map(p => (
              <div key={p} className="bg-slate-700/50 border border-slate-600 rounded-lg p-3 text-center">
                <p className="text-slate-300 text-xs font-medium">{p}</p>
              </div>
            ))}
          </div>
          <p className="text-slate-600 text-xs mt-3">Set LLM_PROVIDER and the corresponding API key in backend/.env</p>
        </div>

        <div className="bg-slate-800/60 border border-slate-700/50 rounded-2xl p-6">
          <h2 className="font-semibold text-white mb-3">About MathVerse AI</h2>
          <div className="space-y-1.5 text-sm text-slate-400">
            <p>Version: <span className="text-slate-300">1.0.0</span></p>
            <p>Backend: <span className="text-slate-300">FastAPI + SymPy + SQLite</span></p>
            <p>Frontend: <span className="text-slate-300">React + TypeScript + Tailwind CSS</span></p>
            <p>AI: <span className="text-slate-300">Anthropic Claude / OpenAI / Gemini</span></p>
          </div>
        </div>
      </div>
    </div>
  )
}
