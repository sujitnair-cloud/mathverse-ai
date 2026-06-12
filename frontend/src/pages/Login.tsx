import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { GoogleLogin, CredentialResponse } from '@react-oauth/google'
import { useAuth } from '../context/AuthContext'

export default function Login() {
  const { user, login, loading } = useAuth()
  const navigate = useNavigate()

  useEffect(() => {
    if (user) navigate('/', { replace: true })
  }, [user, navigate])

  const handleSuccess = async (res: CredentialResponse) => {
    if (!res.credential) return
    try {
      await login(res.credential)
      navigate('/', { replace: true })
    } catch {
      alert('Sign-in failed. Please try again.')
    }
  }

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-10">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white font-bold text-3xl shadow-2xl mx-auto mb-4">
            ∑
          </div>
          <h1 className="text-3xl font-bold text-white">
            Math<span className="text-indigo-400">Verse</span>{' '}
            <span className="text-xs font-medium bg-indigo-500/20 text-indigo-300 px-2 py-0.5 rounded-full align-middle">AI</span>
          </h1>
          <p className="text-slate-400 mt-2">Your complete mathematics learning platform</p>
        </div>

        {/* Card */}
        <div className="bg-slate-800 border border-slate-700 rounded-2xl p-8 shadow-2xl">
          <h2 className="text-xl font-semibold text-white mb-2">Welcome back</h2>
          <p className="text-slate-400 text-sm mb-8">
            Sign in to save your progress, history, and quiz scores across devices.
          </p>

          <div className="flex justify-center mb-6">
            {loading ? (
              <div className="text-slate-400 text-sm animate-pulse">Signing in…</div>
            ) : (
              <GoogleLogin
                onSuccess={handleSuccess}
                onError={() => alert('Google sign-in failed.')}
                theme="filled_black"
                shape="rectangular"
                size="large"
                text="signin_with"
                locale="en"
              />
            )}
          </div>

          <div className="border-t border-slate-700 pt-6">
            <button
              onClick={() => navigate('/')}
              className="w-full py-2.5 rounded-xl text-sm text-slate-400 hover:text-white hover:bg-slate-700/50 transition-all"
            >
              Continue without signing in →
            </button>
          </div>
        </div>

        <p className="text-center text-xs text-slate-600 mt-6">
          By signing in you agree to our Terms of Service and Privacy Policy.
        </p>
      </div>
    </div>
  )
}
