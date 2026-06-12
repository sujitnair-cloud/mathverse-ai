import { useState, useEffect } from 'react'
import { getAdminDashboard } from '../services/api'
import { Shield, Loader2, BarChart2 } from 'lucide-react'

export default function Admin() {
  const [data, setData] = useState<{ stats: Record<string, number>; recent_activity: { problem: string; topic: string; created_at: string }[]; top_topics: { topic: string; count: number }[] } | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getAdminDashboard().then(setData).finally(() => setLoading(false))
  }, [])

  return (
    <div className="animate-fade-in">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white flex items-center gap-3 mb-2">
          <Shield className="text-indigo-400" size={32} />
          Admin Dashboard
        </h1>
        <p className="text-slate-400">Platform usage statistics and activity.</p>
      </div>

      {loading ? (
        <div className="text-center py-12 text-indigo-300"><Loader2 size={32} className="animate-spin mx-auto" /></div>
      ) : data ? (
        <div className="space-y-6">
          {/* Stats grid */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            {Object.entries(data.stats).map(([key, val]) => (
              <div key={key} className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-4 text-center">
                <p className="text-2xl font-bold text-indigo-300">{val}</p>
                <p className="text-slate-400 text-xs mt-1 capitalize">{key.replace(/_/g, ' ')}</p>
              </div>
            ))}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Top topics */}
            <div className="bg-slate-800/60 border border-slate-700/50 rounded-2xl p-5">
              <h2 className="font-semibold text-white mb-4 flex items-center gap-2">
                <BarChart2 size={16} className="text-indigo-400" /> Top Topics
              </h2>
              <div className="space-y-2">
                {data.top_topics.map((t, i) => (
                  <div key={i} className="flex items-center justify-between">
                    <span className="text-slate-300 text-sm capitalize">{t.topic?.replace(/_/g, ' ') || 'Unknown'}</span>
                    <div className="flex items-center gap-2">
                      <div className="h-1.5 bg-indigo-500 rounded-full" style={{ width: `${Math.min(100, t.count * 10)}px` }} />
                      <span className="text-slate-500 text-xs">{t.count}</span>
                    </div>
                  </div>
                ))}
                {data.top_topics.length === 0 && <p className="text-slate-500 text-sm">No data yet.</p>}
              </div>
            </div>

            {/* Recent activity */}
            <div className="bg-slate-800/60 border border-slate-700/50 rounded-2xl p-5">
              <h2 className="font-semibold text-white mb-4">Recent Activity</h2>
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {data.recent_activity.map((a, i) => (
                  <div key={i} className="text-sm border-b border-slate-700/30 pb-2">
                    <p className="text-slate-300 truncate">{a.problem}</p>
                    <span className="text-indigo-400/70 text-xs">{a.topic?.replace(/_/g, ' ')}</span>
                  </div>
                ))}
                {data.recent_activity.length === 0 && <p className="text-slate-500 text-sm">No activity yet.</p>}
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  )
}
