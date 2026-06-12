import { useState, useEffect } from 'react'
import { getUserProfile, saveUserProfile, getSessionId } from '../services/api'
import { User, Save, Loader2 } from 'lucide-react'
import clsx from 'clsx'

const USER_TYPES = ['kids', 'student', 'teacher', 'parent', 'engineer', 'finance', 'researcher']
const LEVELS = ['basic', 'intermediate', 'advanced', 'expert']
const LANGUAGES = [{ code: 'en', label: 'English' }, { code: 'hi', label: 'Hindi' }, { code: 'es', label: 'Spanish' }]

export default function Profile() {
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [form, setForm] = useState({
    username: '',
    user_type: 'student',
    level: 'intermediate',
    preferred_language: 'en',
  })
  const [stats, setStats] = useState({ total_problems_solved: 0, streak_days: 0 })

  useEffect(() => {
    getUserProfile().then(data => {
      if (data.exists) {
        setForm({
          username: data.username || '',
          user_type: data.user_type || 'student',
          level: data.level || 'intermediate',
          preferred_language: data.preferred_language || 'en',
        })
        setStats({ total_problems_solved: data.total_problems_solved || 0, streak_days: data.streak_days || 0 })
      }
    }).finally(() => setLoading(false))
  }, [])

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    await saveUserProfile(form)
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
    setSaving(false)
  }

  return (
    <div className="max-w-2xl mx-auto animate-fade-in">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white flex items-center gap-3 mb-2">
          <User className="text-indigo-400" size={32} />
          Profile
        </h1>
        <p className="text-slate-400">Personalise your MathVerse AI experience.</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-4 mb-6">
        <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-4 text-center">
          <p className="text-3xl font-bold text-indigo-300">{stats.total_problems_solved}</p>
          <p className="text-slate-400 text-sm mt-1">Problems Solved</p>
        </div>
        <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-4 text-center">
          <p className="text-3xl font-bold text-amber-300">{stats.streak_days}</p>
          <p className="text-slate-400 text-sm mt-1">Day Streak 🔥</p>
        </div>
      </div>

      <div className="bg-slate-800/60 border border-slate-700/50 rounded-2xl p-6">
        {loading ? (
          <div className="text-center py-8 text-indigo-300"><Loader2 size={24} className="animate-spin mx-auto" /></div>
        ) : (
          <form onSubmit={handleSave} className="space-y-5">
            <div>
              <label className="text-slate-400 text-sm block mb-1.5">Display Name</label>
              <input
                value={form.username}
                onChange={e => setForm(f => ({ ...f, username: e.target.value }))}
                placeholder="Your name"
                className="w-full bg-slate-700/50 border border-slate-600 rounded-xl px-4 py-2.5 text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm"
              />
            </div>

            <div>
              <label className="text-slate-400 text-sm block mb-2">I am a…</label>
              <div className="flex flex-wrap gap-2">
                {USER_TYPES.map(t => (
                  <button key={t} type="button" onClick={() => setForm(f => ({ ...f, user_type: t }))}
                    className={clsx('px-3 py-1.5 rounded-lg text-sm capitalize transition-all', form.user_type === t ? 'bg-indigo-500/30 border border-indigo-500/50 text-indigo-200' : 'bg-slate-700/50 border border-slate-600 text-slate-400 hover:text-white')}>
                    {t}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="text-slate-400 text-sm block mb-2">Explanation Level</label>
              <div className="flex gap-2">
                {LEVELS.map(l => (
                  <button key={l} type="button" onClick={() => setForm(f => ({ ...f, level: l }))}
                    className={clsx('flex-1 py-2 rounded-lg text-sm capitalize transition-all', form.level === l ? 'bg-indigo-500/30 border border-indigo-500/50 text-indigo-200' : 'bg-slate-700/50 border border-slate-600 text-slate-400 hover:text-white')}>
                    {l}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="text-slate-400 text-sm block mb-1.5">Language</label>
              <select value={form.preferred_language} onChange={e => setForm(f => ({ ...f, preferred_language: e.target.value }))}
                className="bg-slate-700/50 border border-slate-600 text-slate-300 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-indigo-500">
                {LANGUAGES.map(l => <option key={l.code} value={l.code}>{l.label}</option>)}
              </select>
            </div>

            <div className="pt-1 text-xs text-slate-600">Session ID: {getSessionId()}</div>

            <button type="submit" disabled={saving}
              className="w-full bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white py-3 rounded-xl font-semibold transition-colors flex items-center justify-center gap-2">
              {saving ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
              {saved ? '✓ Saved!' : 'Save Profile'}
            </button>
          </form>
        )}
      </div>
    </div>
  )
}
