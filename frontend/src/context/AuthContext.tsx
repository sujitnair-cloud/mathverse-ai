import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import axios from 'axios'
import api from '../services/api'

interface AuthUser {
  id: number
  email: string
  name: string
  avatar_url: string
}

interface AuthContextType {
  user: AuthUser | null
  token: string | null
  loading: boolean
  login: (googleCredential: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextType | null>(null)

const TOKEN_KEY = 'mathverse_token'
const USER_KEY = 'mathverse_user'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(() => {
    try { return JSON.parse(localStorage.getItem(USER_KEY) || 'null') } catch { return null }
  })
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY))
  const [loading, setLoading] = useState(false)

  // Verify stored token on mount
  useEffect(() => {
    if (!token) return
    // Uses the shared `api` client (not raw axios) so this benefits from its
    // retry-on-transient-network-failure interceptor — the intermittent DNS
    // resolution miss for the Railway hostname that broke sign-in previously
    // affects every request equally, not just login itself.
    api.get('/auth/me')
      .then(r => { if (!r.data.authenticated) logout() })
      .catch(error => {
        if (axios.isAxiosError(error) && error.response?.status === 401) logout()
      })
  }, []) // eslint-disable-line

  const login = async (googleCredential: string) => {
    setLoading(true)
    try {
      const { data } = await api.post('/auth/google', { credential: googleCredential })
      if (!data?.access_token) {
        // A service worker (or any proxy) returning a 200 with an
        // unexpected body must not be treated as a successful login —
        // that previously stored the literal string "undefined" as the
        // token and left the UI stuck showing "Sign in" with no error.
        throw new Error('Sign-in response did not include an access token')
      }
      localStorage.setItem(TOKEN_KEY, data.access_token)
      localStorage.setItem(USER_KEY, JSON.stringify(data.user))
      setToken(data.access_token)
      setUser(data.user)
    } finally {
      setLoading(false)
    }
  }

  const logout = () => {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
    setToken(null)
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, token, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
