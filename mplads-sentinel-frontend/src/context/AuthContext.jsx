import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react'
import { api } from '../services/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [auth, setAuth] = useState(() => api.getStoredAuth())
  const [authLoading, setAuthLoading] = useState(
    () => Boolean(api.getStoredAuth()?.access_token),
  )

  useEffect(() => {
    const storedAuth = api.getStoredAuth()

    if (!storedAuth?.access_token) {
      return
    }

    let cancelled = false

    api
      .getMe()
      .then((user) => {
        if (cancelled) return

        const refreshedAuth = {
          ...storedAuth,
          user,
        }

        api.saveAuth(refreshedAuth)
        setAuth(refreshedAuth)
      })
      .catch(() => {
        if (cancelled) return

        api.clearAuth()
        setAuth(null)
      })
      .finally(() => {
        if (!cancelled) {
          setAuthLoading(false)
        }
      })

    return () => {
      cancelled = true
    }
  }, [])

  const logout = () => {
    api.clearAuth()
    setAuth(null)
  }

  const value = useMemo(
    () => ({
      auth,
      user: auth?.user || null,
      token: auth?.access_token || null,
      isAdmin: auth?.user?.role === 'admin',
      authLoading,
      logout,
    }),
    [auth, authLoading],
  )

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)

  if (!context) {
    throw new Error('useAuth must be used inside AuthProvider')
  }

  return context
}