/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { api } from '../api'

const AuthContext = createContext(null)

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth deve ser usado dentro de AuthProvider')
  return context
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get('/accounts/api/csrf/').catch(() => {})
    api.get('/accounts/api/me/')
      .then((data) => setUser(data))
      .catch(() => setUser(null))
      .finally(() => setLoading(false))
  }, [])

  const login = useCallback(async (username, password) => {
    const data = await api.post('/accounts/api/login/', { username, password })
    setUser(data)
  }, [])

  const signup = useCallback(async (username, email, password1, password2) => {
    const data = await api.post('/accounts/api/signup/', {
      username, email, password1, password2,
    })
    setUser(data)
  }, [])

  const logout = useCallback(async () => {
    await api.post('/accounts/api/logout/', {})
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, loading, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  )
}
