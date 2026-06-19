import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useTheme } from '../hooks/useTheme'
import { useAuth } from '../context/AuthContext'
import {
  Sun, Moon, Calculator, BookOpen, Library, BarChart2,
  Trophy, History, Settings, Menu, X, LogOut, User
} from 'lucide-react'
import { useState, useRef, useEffect } from 'react'
import clsx from 'clsx'

const NAV_ITEMS = [
  { to: '/solver', label: 'AI Solver', icon: Calculator },
  { to: '/formulas', label: 'Formulas', icon: Library },
  { to: '/topics', label: 'Topics', icon: BookOpen },
  { to: '/graph', label: 'Graphing', icon: BarChart2 },
  { to: '/quiz', label: 'Quiz', icon: Trophy },
  { to: '/history', label: 'History', icon: History },
]

export default function Navbar() {
  const { isDark, toggle } = useTheme()
  const location = useLocation()
  const navigate = useNavigate()
  const { user, logout } = useAuth()
  const [menuOpen, setMenuOpen] = useState(false)
  const [userMenuOpen, setUserMenuOpen] = useState(false)
  const userMenuRef = useRef<HTMLDivElement>(null)

  // Close user menu on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target as Node)) {
        setUserMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  return (
    <nav className="sticky top-0 z-50 bg-slate-900/95 backdrop-blur border-b border-slate-700/50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2 group">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white font-bold text-xl shadow-lg group-hover:scale-110 transition-transform">
              ∑
            </div>
            <span className="hidden sm:block font-bold text-lg text-white">
              Math<span className="text-indigo-400">Verse</span>{' '}
              <span className="text-xs font-medium bg-indigo-500/20 text-indigo-300 px-1.5 py-0.5 rounded-full">AI</span>
            </span>
          </Link>

          {/* Desktop Nav */}
          <div className="hidden md:flex items-center gap-1">
            {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
              <Link
                key={to}
                to={to}
                className={clsx(
                  'flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-all',
                  location.pathname === to
                    ? 'bg-indigo-500/20 text-indigo-300'
                    : 'text-slate-400 hover:text-white hover:bg-slate-700/50'
                )}
              >
                <Icon size={15} />
                {label}
              </Link>
            ))}
          </div>

          {/* Right side */}
          <div className="flex items-center gap-2">
            <button
              onClick={toggle}
              className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-700/50 transition-all"
              aria-label="Toggle theme"
            >
              {isDark ? <Sun size={18} /> : <Moon size={18} />}
            </button>

            <Link
              to="/settings"
              className={clsx(
                'p-2 rounded-lg transition-all',
                location.pathname === '/settings'
                  ? 'text-indigo-300 bg-indigo-500/20'
                  : 'text-slate-400 hover:text-white hover:bg-slate-700/50'
              )}
            >
              <Settings size={18} />
            </Link>

            {/* User avatar or sign-in */}
            <Link
              to="/pricing"
              className={clsx(
                'hidden md:flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium border transition-all',
                location.pathname === '/pricing'
                  ? 'border-indigo-500/50 bg-indigo-500/15 text-indigo-300'
                  : 'border-slate-600 text-slate-400 hover:border-indigo-500/40 hover:text-indigo-300'
              )}
            >
              ⚡ Upgrade
            </Link>

            {user ? (
              <div className="relative" ref={userMenuRef}>
                <button
                  onClick={() => setUserMenuOpen(o => !o)}
                  className="flex items-center gap-2 p-1 rounded-lg hover:bg-slate-700/50 transition-all"
                >
                  {user.avatar_url ? (
                    <img src={user.avatar_url} alt={user.name} className="w-8 h-8 rounded-full ring-2 ring-indigo-500/40" />
                  ) : (
                    <div className="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center text-white text-sm font-bold">
                      {user.name?.[0]?.toUpperCase() ?? '?'}
                    </div>
                  )}
                </button>

                {userMenuOpen && (
                  <div className="absolute right-0 mt-2 w-52 bg-slate-800 border border-slate-700 rounded-xl shadow-xl py-1 animate-fade-in z-50">
                    <div className="px-4 py-3 border-b border-slate-700">
                      <p className="text-white text-sm font-medium truncate">{user.name}</p>
                      <p className="text-slate-400 text-xs truncate">{user.email}</p>
                    </div>
                    <button
                      onClick={() => { navigate('/profile'); setUserMenuOpen(false) }}
                      className="flex items-center gap-2 w-full px-4 py-2.5 text-sm text-slate-300 hover:bg-slate-700/50 hover:text-white transition-all"
                    >
                      <User size={15} /> Profile
                    </button>
                    <button
                      onClick={() => { logout(); setUserMenuOpen(false) }}
                      className="flex items-center gap-2 w-full px-4 py-2.5 text-sm text-red-400 hover:bg-red-500/10 hover:text-red-300 transition-all"
                    >
                      <LogOut size={15} /> Sign out
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <button
                onClick={() => navigate('/login')}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium bg-indigo-600 hover:bg-indigo-500 text-white transition-all"
              >
                <User size={15} /> Sign in
              </button>
            )}

            {/* Mobile menu toggle */}
            <button
              className="md:hidden p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-700/50"
              onClick={() => setMenuOpen(o => !o)}
            >
              {menuOpen ? <X size={20} /> : <Menu size={20} />}
            </button>
          </div>
        </div>

        {/* Mobile menu */}
        {menuOpen && (
          <div className="md:hidden pb-3 border-t border-slate-700/50 pt-2 animate-fade-in">
            {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
              <Link
                key={to}
                to={to}
                onClick={() => setMenuOpen(false)}
                className={clsx(
                  'flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm font-medium transition-all mb-0.5',
                  location.pathname === to
                    ? 'bg-indigo-500/20 text-indigo-300'
                    : 'text-slate-400 hover:text-white hover:bg-slate-700/50'
                )}
              >
                <Icon size={16} />
                {label}
              </Link>
            ))}
          </div>
        )}
      </div>
    </nav>
  )
}
