import { Link, useLocation } from 'react-router-dom'
import { Calculator, Library, Trophy, History, Grid3x3 } from 'lucide-react'
import clsx from 'clsx'

const TABS = [
  { to: '/solver',   label: 'Solver',   icon: Calculator },
  { to: '/formulas', label: 'Formulas', icon: Library },
  { to: '/quiz',     label: 'Quiz',     icon: Trophy },
  { to: '/history',  label: 'History',  icon: History },
  { to: '/topics',   label: 'Topics',   icon: Grid3x3 },
]

export default function BottomNav() {
  const location = useLocation()

  return (
    /* Only visible on mobile screens, hidden on md+ */
    <nav className="md:hidden fixed bottom-0 left-0 right-0 z-50 bg-slate-900/95 backdrop-blur-md border-t border-slate-700/60 pb-safe">
      <div className="flex items-stretch h-16">
        {TABS.map(({ to, label, icon: Icon }) => {
          const active = location.pathname === to
          return (
            <Link
              key={to}
              to={to}
              className={clsx(
                'flex-1 flex flex-col items-center justify-center gap-0.5 transition-all active:scale-95',
                active ? 'text-indigo-400' : 'text-slate-500'
              )}
            >
              <div className={clsx(
                'p-1.5 rounded-xl transition-all',
                active && 'bg-indigo-500/20'
              )}>
                <Icon size={20} strokeWidth={active ? 2.5 : 1.8} />
              </div>
              <span className={clsx(
                'text-[10px] font-medium leading-none',
                active ? 'text-indigo-300' : 'text-slate-500'
              )}>
                {label}
              </span>
            </Link>
          )
        })}
      </div>
    </nav>
  )
}
