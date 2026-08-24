import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'
import { ProtectedRoute } from './components/ProtectedRoute'
import { Login } from './pages/Login'
import { Signup } from './pages/Signup'
import { Dashboard } from './pages/Dashboard'
import { Perfil } from './pages/Perfil'
import { Busca } from './pages/Busca'
import { Historico } from './pages/Historico'
import { Revisao } from './pages/Revisao'
import { Fontes } from './pages/Fontes'
import './App.css'

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />
          <Route
            path="/perfil"
            element={
              <ProtectedRoute>
                <Perfil />
              </ProtectedRoute>
            }
          />
          <Route
            path="/busca"
            element={
              <ProtectedRoute>
                <Busca />
              </ProtectedRoute>
            }
          />
          <Route
            path="/historico"
            element={
              <ProtectedRoute>
                <Historico />
              </ProtectedRoute>
            }
          />
          <Route
            path="/fontes"
            element={
              <ProtectedRoute staff>
                <Fontes />
              </ProtectedRoute>
            }
          />
          <Route
            path="/revisao"
            element={
              <ProtectedRoute staff>
                <Revisao />
              </ProtectedRoute>
            }
          />
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App
