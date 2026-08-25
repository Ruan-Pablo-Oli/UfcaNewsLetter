import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { useNavigate, Link } from 'react-router-dom'
import { api } from '../api'
import { Esqueleto } from '../components/Esqueleto'

export function Busca() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const [q, setQ] = useState('')
  const [categoria, setCategoria] = useState('')
  const [curso, setCurso] = useState('')
  const [dataInicio, setDataInicio] = useState('')
  const [dataFim, setDataFim] = useState('')
  const [categorias, setCategorias] = useState([])
  const [cursos, setCursos] = useState([])
  const [resultados, setResultados] = useState([])
  const [count, setCount] = useState(0)
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [loading, setLoading] = useState(false)
  const [buscou, setBuscou] = useState(false)

  useEffect(() => {
    async function loadFiltros() {
      try {
        const [c, cr] = await Promise.all([
          api.get('/accounts/api/cursos/'),
          api.get('/feed/'),
        ])
        setCursos(c.cursos)
        const cats = new Set((cr.results || []).map((i) => i.categoria).filter(Boolean))
        setCategorias([...cats])
      } catch { /* filtros são opcionais */ }
    }
    loadFiltros()
  }, [])

  const executarBusca = useCallback(async (p) => {
    setLoading(true)
    setBuscou(true)
    try {
      const query = new URLSearchParams()
      if (q) query.set('q', q)
      if (categoria) query.set('categoria', categoria)
      if (curso) query.set('curso', curso)
      if (dataInicio) query.set('data_inicio', dataInicio)
      if (dataFim) query.set('data_fim', dataFim)
      query.set('page', p)
      const data = await api.get(`/busca/?${query.toString()}`)
      setResultados(data.results)
      setCount(data.count)
      setTotalPages(data.total_pages)
      setPage(data.page)
    } catch {
      setResultados([])
      setCount(0)
    } finally {
      setLoading(false)
    }
  }, [q, categoria, curso, dataInicio, dataFim])

  function handleSubmit(e) {
    e.preventDefault()
    executarBusca(1)
  }

  function limpar() {
    setQ('')
    setCategoria('')
    setCurso('')
    setDataInicio('')
    setDataFim('')
    setBuscou(false)
    setResultados([])
    setCount(0)
  }

  async function handleLogout() {
    await logout()
    navigate('/login')
  }

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <div className="dashboard-header-left">
          <img src="/logo.svg" alt="UFCA Newsletter" className="dashboard-logo" />
        </div>
        <div className="dashboard-header-right">
          <span className="dashboard-user">{user?.username}</span>
          <Link to="/perfil" className="dashboard-link">Perfil</Link>
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
            <Link to="/busca" className="dashboard-nav-item active">
              <span className="nav-icon">🔎</span>
              Buscar
            </Link>
            <Link to="/historico" className="dashboard-nav-item">
              <span className="nav-icon">🕘</span>
              Histórico
            </Link>
            <Link to="/perfil" className="dashboard-nav-item">
              <span className="nav-icon">👤</span>
              Perfil Acadêmico
            </Link>
          </nav>
        </aside>

        <main className="dashboard-main">
          <h2 className="dashboard-title">Buscar conteúdos</h2>
          <p className="dashboard-subtitle">
            Encontre editais, comunicados, eventos e prazos visíveis ao seu perfil.
          </p>

          <form className="busca-form" onSubmit={handleSubmit}>
            <div className="busca-row">
              <input
                type="text"
                className="feed-search"
                placeholder="Palavra-chave (título ou texto)..."
                aria-label="Palavra-chave"
                value={q}
                onChange={(e) => setQ(e.target.value)}
              />
              <button type="submit" className="dashboard-btn" disabled={loading}>
                {loading ? 'Buscando...' : 'Buscar'}
              </button>
            </div>

            <div className="busca-filtros">
              <select
                aria-label="Filtrar por categoria"
                value={categoria}
                onChange={(e) => setCategoria(e.target.value)}
              >
                <option value="">Todas as categorias</option>
                {categorias.map((cat) => (
                  <option key={cat} value={cat}>{cat}</option>
                ))}
              </select>

              <select
                aria-label="Filtrar por curso"
                value={curso}
                onChange={(e) => setCurso(e.target.value)}
              >
                <option value="">Todos os cursos</option>
                {cursos.map((c) => (
                  <option key={c.value} value={c.value}>{c.label}</option>
                ))}
              </select>

              <input
                type="date"
                aria-label="Data inicial"
                value={dataInicio}
                onChange={(e) => setDataInicio(e.target.value)}
              />
              <span className="busca-sep">até</span>
              <input
                type="date"
                aria-label="Data final"
                value={dataFim}
                onChange={(e) => setDataFim(e.target.value)}
              />

              <button type="button" className="filter-btn" onClick={limpar}>Limpar</button>
            </div>
          </form>

          {loading && <Esqueleto linhas={3} />}

          {!loading && buscou && count === 0 && (
            <div className="feed-empty">
              Nenhum resultado encontrado com esses filtros.
            </div>
          )}

          {!buscou && !loading && (
            <div className="feed-empty">
              Digite uma palavra-chave ou use os filtros para buscar conteúdos.
            </div>
          )}

          <div className="feed-list">
            {resultados.map((item) => (
              <div key={item.id} className="feed-card"
                  data-categoria={item.categoria || undefined}>
                <div className="feed-card-header">
                  <span className="feed-category">{item.categoria}</span>
                  <span className="feed-source">{item.fonte}</span>
                  <span className="feed-date">
                    {new Date(item.data_publicacao).toLocaleDateString('pt-BR')}
                  </span>
                </div>
                <h3 className="feed-title">{item.titulo}</h3>
                {item.resumo && <p className="feed-summary">{item.resumo}</p>}
                {item.url && (
                  <a
                    className="feed-link"
                    href={item.url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Ver conteúdo original
                  </a>
                )}
              </div>
            ))}
          </div>

          {totalPages > 1 && (
            <div className="feed-pagination">
              <button className="pagination-btn" disabled={page <= 1} onClick={() => executarBusca(page - 1)}>
                Anterior
              </button>
              <span className="pagination-info">{page} / {totalPages}</span>
              <button className="pagination-btn" disabled={page >= totalPages} onClick={() => executarBusca(page + 1)}>
                Próxima
              </button>
            </div>
          )}
        </main>
      </div>
    </div>
  )
}
