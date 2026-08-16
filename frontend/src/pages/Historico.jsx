import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { useNavigate, Link } from 'react-router-dom'
import { api } from '../api'

export function Historico() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const [dataInicio, setDataInicio] = useState('')
  const [dataFim, setDataFim] = useState('')
  const [categoria, setCategoria] = useState('')
  const [categorias, setCategorias] = useState([])
  const [itens, setItens] = useState([])
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function loadCategorias() {
      try {
        const feed = await api.get('/feed/')
        const cats = new Set((feed.results || []).map((i) => i.categoria).filter(Boolean))
        setCategorias([...cats])
      } catch { /* opcional */ }
    }
    loadCategorias()
  }, [])

  const fetchHistorico = useCallback(async (p, params = {}) => {
    setLoading(true)
    try {
      const query = new URLSearchParams()
      if (params.dataInicio || dataInicio) query.set('data_inicio', params.dataInicio || dataInicio)
      if (params.dataFim || dataFim) query.set('data_fim', params.dataFim || dataFim)
      if (params.categoria || categoria) query.set('categoria', params.categoria || categoria)
      query.set('page', p)
      const data = await api.get(`/historico/?${query.toString()}`)
      setItens(data.results)
      setTotalPages(data.total_pages)
      setPage(data.page)
    } catch {
      setItens([])
    } finally {
      setLoading(false)
    }
  }, [dataInicio, dataFim, categoria])

  // `set-state-in-effect` sinaliza qualquer setState alcançável pelo efeito,
  // inclusive depois do `await`. Aqui a atualização só ocorre quando a resposta
  // de `GET /historico/` chega — busca de dados na montagem, não render em cascata.
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { fetchHistorico(1) }, [fetchHistorico])

  function handleFiltros(e) {
    e.preventDefault()
    fetchHistorico(1)
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
            <Link to="/busca" className="dashboard-nav-item">
              <span className="nav-icon">🔎</span>
              Buscar
            </Link>
            <Link to="/historico" className="dashboard-nav-item active">
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
          <h2 className="dashboard-title">Histórico de entregas</h2>
          <p className="dashboard-subtitle">
            Conteúdos que você já recebeu, em ordem cronológica.
          </p>

          <form className="busca-form" onSubmit={handleFiltros}>
            <div className="busca-filtros">
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
              <button type="submit" className="dashboard-btn">Filtrar</button>
            </div>
          </form>

          {loading && <p style={{ marginTop: 32, color: '#999' }}>Carregando...</p>}

          {!loading && itens.length === 0 && (
            <div className="feed-empty">
              Nenhum conteúdo entregue ainda. As entregas aparecem aqui quando
              você recebe conteúdos pelos canais configurados.
            </div>
          )}

          <div className="feed-list">
            {itens.map((item) => (
              <div key={item.id} className="feed-card">
                <div className="feed-card-header">
                  <span className="feed-category">{item.categoria}</span>
                  <span className="feed-source">{item.fonte}</span>
                  <span className="feed-date">
                    {new Date(item.data_envio).toLocaleDateString('pt-BR')}
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
              <button className="pagination-btn" disabled={page <= 1} onClick={() => fetchHistorico(page - 1)}>
                Anterior
              </button>
              <span className="pagination-info">{page} / {totalPages}</span>
              <button className="pagination-btn" disabled={page >= totalPages} onClick={() => fetchHistorico(page + 1)}>
                Próxima
              </button>
            </div>
          )}
        </main>
      </div>
    </div>
  )
}
