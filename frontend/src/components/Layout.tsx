import { Outlet } from 'react-router-dom'
import Navbar from './Navbar'
import BottomNav from './BottomNav'

export default function Layout() {
  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 transition-colors">
      <Navbar />

      {/* Extra bottom padding on mobile so content isn't hidden behind BottomNav */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6 pb-24 md:pb-8">
        <Outlet />
      </main>

      <footer className="border-t border-slate-700/50 mt-16 py-8 text-center text-slate-500 text-sm hidden md:block">
        <p>
          MathVerse AI — Your complete mathematics learning platform{' '}
          <span className="text-indigo-400">∑</span>
        </p>
        <p className="mt-1 text-xs">Powered by SymPy · FastAPI · React · Tailwind CSS</p>
        <div className="flex items-center justify-center gap-4 mt-3 text-xs">
          <a href="/privacy" className="hover:text-indigo-400 transition-colors">Privacy Policy</a>
          <span>·</span>
          <a href="/terms" className="hover:text-indigo-400 transition-colors">Terms of Service</a>
          <span>·</span>
          <a href="/pricing" className="hover:text-indigo-400 transition-colors">Pricing</a>
        </div>
      </footer>

      <BottomNav />
    </div>
  )
}
