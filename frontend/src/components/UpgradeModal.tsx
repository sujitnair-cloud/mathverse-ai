import { Zap, LogIn, X } from 'lucide-react'

interface Props {
  message: string
  isSignedIn: boolean
  onSignIn: () => void
  onUpgrade: () => void
  onClose: () => void
}

// A real modal (not an inline banner) for the free-limit paywall — easy to
// miss scrolling past an inline card, but a modal forces the moment where a
// trial user actually has to decide to sign in / upgrade. Sized and padded
// to stay comfortable on a phone screen (safe side margins, capped height
// with internal scroll for very short viewports).
export default function UpgradeModal({ message, isSignedIn, onSignIn, onUpgrade, onClose }: Props) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4 py-6"
      onClick={onClose}
    >
      <div
        className="w-full max-w-sm max-h-[90vh] overflow-y-auto bg-slate-800 border border-indigo-500/40 rounded-2xl p-6 shadow-2xl animate-slide-up"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between mb-4">
          <div className="w-10 h-10 rounded-xl bg-indigo-500/20 flex items-center justify-center flex-shrink-0">
            <Zap size={20} className="text-indigo-400" />
          </div>
          <button
            onClick={onClose}
            aria-label="Close"
            className="text-slate-400 hover:text-white p-1 -m-1"
          >
            <X size={20} />
          </button>
        </div>
        <p className="text-white font-semibold text-lg mb-1">
          You've used all your free solves
        </p>
        <p className="text-slate-300 text-sm mb-5">{message}</p>
        {!isSignedIn ? (
          <button
            onClick={onSignIn}
            className="w-full inline-flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-5 py-3 rounded-xl font-medium text-sm transition-colors"
          >
            <LogIn size={16} />
            Sign in with Google — it's free
          </button>
        ) : (
          <button
            onClick={onUpgrade}
            className="w-full inline-flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-5 py-3 rounded-xl font-medium text-sm transition-colors"
          >
            <Zap size={16} />
            Upgrade to Pro
          </button>
        )}
        <button
          onClick={onClose}
          className="w-full text-center text-slate-400 hover:text-slate-300 text-sm mt-3 py-1"
        >
          Maybe later
        </button>
      </div>
    </div>
  )
}
