/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { api, EVENTO_SESSAO_EXPIRADA } from '../api'

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

  // Quando qualquer chamada esbarra numa sessão caída, o app inteiro volta ao
  // estado deslogado — o ProtectedRoute então manda para o login, em vez de
  // deixar a tela presa mostrando um erro.
  useEffect(() => {
    const aoExpirar = () => setUser(null)
    window.addEventListener(EVENTO_SESSAO_EXPIRADA, aoExpirar)
    return () => window.removeEventListener(EVENTO_SESSAO_EXPIRADA, aoExpirar)
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
