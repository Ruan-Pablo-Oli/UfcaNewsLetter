import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { api } from '../api'

export function Perfil() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const [tab, setTab] = useState('curso')
  const [cursos, setCursos] = useState([])
  const [interessesList, setInteressesList] = useState([])
  const [curso, setCurso] = useState('')
  const [periodo, setPeriodo] = useState(1)
  const [interesses, setInteresses] = useState([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  useEffect(() => {
    async function load() {
      try {
        const [perfil, c, i] = await Promise.all([
          api.get('/accounts/api/perfil/'),
          api.get('/accounts/api/cursos/'),
          api.get('/accounts/api/interesses/'),
        ])
        setCurso(perfil.curso)
        setPeriodo(perfil.periodo)
        setInteresses(perfil.interesses || [])
        setCursos(c.cursos)
        setInteressesList(i.interesses)
      } catch {
        setError('Erro ao carregar perfil.')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  function toggleInteresse(id) {
    setInteresses((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]
    )
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setSuccess('')
    setSaving(true)
    try {
      await api.patch('/accounts/api/perfil/', { curso, periodo, interesses })
      setSuccess('Perfil atualizado com sucesso!')
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  async function handleLogout() {
    await logout()
    navigate('/login')
  }

  const cursoLabel = cursos.find((c) => c.value === curso)?.label || 'Não definido'

  if (loading) {
    return (
      <div className="dashboard">
        <header className="dashboard-header">
          <div className="dashboard-header-left">
            <img src="/logo.svg" alt="UFCA Newsletter" className="dashboard-logo" />
          </div>
        </header>
        <div className="dashboard-body" style={{ justifyContent: 'center', alignItems: 'center' }}>
          <p style={{ color: '#999' }}>Carregando...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <div className="dashboard-header-left">
          <img src="/logo.svg" alt="UFCA Newsletter" className="dashboard-logo" />
        </div>
        <div className="dashboard-header-right">
          <span className="dashboard-user">{user?.username}</span>
          <button className="dashboard-btn" onClick={handleLogout}>Sair</button>
        </div>
      </header>

      <div className="dashboard-body">
        <aside className="dashboard-sidebar">
          <nav className="dashboard-nav">
            <Link to="/" className="dashboard-nav-item">
              <span className="nav-icon">📰</span>
              Feed
            </Link>
            <Link to="/perfil" className="dashboard-nav-item active">
              <span className="nav-icon">👤</span>
              Perfil Acadêmico
            </Link>
          </nav>
        </aside>

        <main className="dashboard-main">
          <div className="perfil-header-card">
            <div className="perfil-avatar">
              {user?.username?.charAt(0).toUpperCase()}
            </div>
            <div className="perfil-header-info">
              <h2>{user?.username}</h2>
              <p>{user?.email}</p>
              <span className="perfil-curso-tag">{cursoLabel} · {periodo}º período</span>
            </div>
          </div>

          <div className="perfil-tabs">
            <button
              className={`perfil-tab ${tab === 'curso' ? 'active' : ''}`}
              onClick={() => setTab('curso')}
            >Curso e Período</button>
            <button
              className={`perfil-tab ${tab === 'interesses' ? 'active' : ''}`}
              onClick={() => setTab('interesses')}
            >
              Interesses
              {interesses.length > 0 && (
                <span className="perfil-tab-count">{interesses.length}</span>
              )}
            </button>
          </div>

          {error && <p className="error-message">{error}</p>}
          {success && <p className="success-message">{success}</p>}

          <form onSubmit={handleSubmit} className="perfil-form">
            {tab === 'curso' && (
              <>
                <div className="input-group">
                  <label htmlFor="curso">Curso</label>
                  <select
                    id="curso"
                    value={curso}
                    onChange={(e) => setCurso(e.target.value)}
                    className="input-select"
                  >
                    <option value="">Selecione seu curso</option>
                    {cursos.map((c) => (
                      <option key={c.value} value={c.value}>{c.label}</option>
                    ))}
                  </select>
                </div>

                <div className="input-group">
                  <label htmlFor="periodo">Período</label>
                  <select
                    id="periodo"
                    value={periodo}
                    onChange={(e) => setPeriodo(Number(e.target.value))}
                    className="input-select"
                  >
                    {Array.from({ length: 20 }, (_, i) => i + 1).map((p) => (
                      <option key={p} value={p}>{p}º período</option>
                    ))}
                  </select>
                </div>
              </>
            )}

            {tab === 'interesses' && (
              <div className="input-group">
                <label>Áreas de interesse (máx. 5)</label>
                <div className="interesses-grid">
                  {interessesList.map((item) => (
                    <label
                      key={item.id}
                      className={`interesse-tag ${interesses.includes(item.id) ? 'selected' : ''}`}
                    >
                      <input
                        type="checkbox"
                        checked={interesses.includes(item.id)}
                        onChange={() => toggleInteresse(item.id)}
                        className="interesse-checkbox"
                      />
                      {item.nome}
                    </label>
                  ))}
                </div>
              </div>
            )}

            <button type="submit" className="login-btn" disabled={saving} style={{ maxWidth: 200 }}>
              {saving ? 'Salvando...' : 'Salvar alterações'}
            </button>
          </form>
        </main>
      </div>
    </div>
  )
}
