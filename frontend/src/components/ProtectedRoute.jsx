import { Navigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

/**
 * Rota autenticada. Com `staff`, exige `is_staff` — o backend já barra
 * (user_passes_test), mas sem isso o estudante veria a tela carregar e só
 * então receber 403.
 */
export function ProtectedRoute({ children, staff = false }) {
  const { user, loading } = useAuth()

  if (loading) return <div>Carregando...</div>
  if (!user) return <Navigate to="/login" replace />
  if (staff && !user.is_staff) return <Navigate to="/" replace />

  return children
}
