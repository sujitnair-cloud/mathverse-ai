import { BookOpen, Calculator, BarChart2, Shield, Zap, Users } from 'lucide-react'

const FEATURES = [
  { icon: Calculator, title: 'AI Math Solver', desc: 'Solves algebra, calculus, geometry, statistics, and more using SymPy + LLM.' },
  { icon: BookOpen, title: 'Math Wikipedia', desc: 'Searchable knowledge base with definitions, formulas, and examples.' },
  { icon: BarChart2, title: 'Graphing Calculator', desc: 'Interactive 2D/3D function plots powered by Plotly.' },
  { icon: Zap, title: 'Step-by-Step', desc: 'Every solution comes with clear, numbered steps and formulas used.' },
  { icon: Shield, title: 'Multi-Level', desc: 'Explanations from kids to expert level — switch anytime.' },
  { icon: Users, title: 'For Everyone', desc: 'Students, teachers, engineers, parents, and competitive exam aspirants.' },
]

export default function About() {
  return (
    <div className="max-w-3xl mx-auto animate-fade-in">
      <div className="text-center py-12">
        <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white font-bold text-5xl mx-auto mb-6 shadow-xl">
          ∑
        </div>
        <h1 className="text-4xl font-extrabold text-white mb-4">
          Math<span className="text-indigo-400">Verse</span> AI
        </h1>
        <p className="text-slate-400 text-lg max-w-xl mx-auto">
          Your complete mathematics learning and solving platform — from basic arithmetic to advanced engineering mathematics.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-12">
        {FEATURES.map(({ icon: Icon, title, desc }) => (
          <div key={title} className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-5">
            <div className="w-9 h-9 rounded-xl bg-indigo-500/15 flex items-center justify-center mb-3">
              <Icon size={18} className="text-indigo-400" />
            </div>
            <h3 className="font-semibold text-white mb-1">{title}</h3>
            <p className="text-slate-400 text-sm">{desc}</p>
          </div>
        ))}
      </div>

      <div className="bg-gradient-to-r from-indigo-900/30 to-purple-900/30 border border-indigo-500/20 rounded-2xl p-8 text-center">
        <h2 className="text-2xl font-bold text-white mb-3">Open Source & Commercial Ready</h2>
        <p className="text-slate-400 text-sm leading-relaxed max-w-xl mx-auto">
          MathVerse AI is built with a modular, scalable architecture. The subscription-ready backend, role-based access control structure, and API-first design make it ready for commercial deployment in schools, coaching centers, and enterprises.
        </p>
        <div className="mt-6 flex flex-wrap justify-center gap-3 text-xs text-slate-400">
          <span className="bg-slate-800 px-3 py-1.5 rounded-full border border-slate-700">Python FastAPI</span>
          <span className="bg-slate-800 px-3 py-1.5 rounded-full border border-slate-700">React + TypeScript</span>
          <span className="bg-slate-800 px-3 py-1.5 rounded-full border border-slate-700">SymPy Math Engine</span>
          <span className="bg-slate-800 px-3 py-1.5 rounded-full border border-slate-700">Tailwind CSS</span>
          <span className="bg-slate-800 px-3 py-1.5 rounded-full border border-slate-700">SQLite → PostgreSQL</span>
          <span className="bg-slate-800 px-3 py-1.5 rounded-full border border-slate-700">Claude / GPT-4 / Gemini</span>
        </div>
      </div>
    </div>
  )
}
