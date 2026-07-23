import { useState, useEffect, useMemo } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { useNavigate, Link } from 'react-router-dom'
import { api } from '../api'

export function Dashboard() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const [feed, setFeed] = useState([])
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [filterCat, setFilterCat] = useState('')
  const [modalItem, setModalItem] = useState(null)

  async function loadFeed(p) {
    setLoading(true)
    try {
      const data = await api.get(`/feed/?page=${p}&page_size=20`)
      setFeed(data.results)
      setTotalPages(data.total_pages)
      setPage(data.page)
    } catch {
      setFeed([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadFeed(1) }, [])

  const categorias = useMemo(() => {
    const cats = new Set(feed.map((i) => i.categoria).filter(Boolean))
    return [...cats]
  }, [feed])

  const filtered = useMemo(() => {
    let items = feed
    if (filterCat) items = items.filter((i) => i.categoria === filterCat)
    if (search) {
      const s = search.toLowerCase()
      items = items.filter(
        (i) =>
          i.titulo?.toLowerCase().includes(s) ||
          i.resumo?.toLowerCase().includes(s)
      )
    }
    return items
  }, [feed, filterCat, search])

  async function handleLogout() {
    await logout()
    navigate('/login')
  }

  async function handleFeedback(conteudoId, tipo) {
    try {
      await api.post('/feedback/', { conteudo_id: conteudoId, tipo })
      setFeed((prev) =>
        prev.map((item) =>
          item.id === conteudoId ? { ...item, feedback: tipo } : item
        )
      )
    } catch { /* ignore */ }
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
            <Link to="/" className="dashboard-nav-item active">
              <span className="nav-icon">📰</span>
              Feed
            </Link>
            <Link to="/perfil" className="dashboard-nav-item">
              <span className="nav-icon">👤</span>
              Perfil Acadêmico
            </Link>
          </nav>
        </aside>

        <main className="dashboard-main">
          <div className="feed-topbar">
            <div>
              <h2 className="dashboard-title">Feed de Notícias</h2>
              <p className="dashboard-subtitle">
                Bem-vindo(a), {user?.username}!
              </p>
            </div>
            <input
              type="text"
              className="feed-search"
              placeholder="Buscar notícias..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>

          <div className="dashboard-cards" style={{ marginBottom: 32 }}>
            <div className="dash-card">
              <div className="dash-card-icon" style={{ background: 'rgba(150, 100, 7, 0.15)' }}>
                <span style={{ fontSize: 28 }}>📊</span>
              </div>
              <div>
                <h3>Feed</h3>
                <p>Acompanhe as notícias e novidades da UFCA</p>
              </div>
            </div>

            <div className="dash-card">
              <div className="dash-card-icon" style={{ background: 'rgba(83,43,29,0.1)' }}>
                <span style={{ fontSize: 28 }}>🎓</span>
              </div>
              <div>
                <h3>Perfil</h3>
                <p>Gerencie seu curso, período e interesses</p>
              </div>
            </div>

            <div className="dash-card">
              <div className="dash-card-icon" style={{ background: 'rgba(117,183,71,0.15)' }}>
                <span style={{ fontSize: 28 }}>📬</span>
              </div>
              <div>
                <h3>Newsletter</h3>
                <p>Receba conteúdos personalizados</p>
              </div>
            </div>
          </div>

          {categorias.length > 0 && (
            <div className="feed-filters">
              <button
                className={`filter-btn ${!filterCat ? 'active' : ''}`}
                onClick={() => setFilterCat('')}
              >Todas</button>
              {categorias.map((cat) => (
                <button
                  key={cat}
                  className={`filter-btn ${filterCat === cat ? 'active' : ''}`}
                  onClick={() => setFilterCat(cat)}
                >{cat}</button>
              ))}
            </div>
          )}

          {loading && page === 1 && (
            <p style={{ marginTop: 32, color: '#999' }}>Carregando...</p>
          )}

          {!loading && filtered.length === 0 && (
            <div className="feed-empty">
              {search || filterCat
                ? 'Nenhum resultado encontrado.'
                : 'Ainda não há conteúdos no seu feed.'}
              {' '}<Link to="/perfil">Complete seu perfil</Link> para receber notícias personalizadas.
            </div>
          )}

          <div className="feed-list">
            {filtered.map((item) => {
              return (
                <div
                  key={item.id}
                  className="feed-card"
                  onClick={() => setModalItem(item)}
                >
                  <div className="feed-card-header">
                    <span className="feed-category">{item.categoria}</span>
                    <span className="feed-source">{item.fonte}</span>
                    <span className="feed-date">
                      {new Date(item.data_publicacao).toLocaleDateString('pt-BR')}
                    </span>
                  </div>
                  <h3 className="feed-title">{item.titulo}</h3>
                  {item.resumo && <p className="feed-summary">{item.resumo}</p>}
                  {item.motivo && (
                    <p className="feed-reason">{item.motivo}</p>
                  )}
                  <div className="feed-actions" onClick={(e) => e.stopPropagation()}>
                    <button
                      className={`feed-btn like ${item.feedback === 'positivo' ? 'active' : ''}`}
                      onClick={() => handleFeedback(item.id, 'positivo')}
                      title="Útil"
                    >👍</button>
                    <button
                      className={`feed-btn dislike ${item.feedback === 'negativo' ? 'active' : ''}`}
                      onClick={() => handleFeedback(item.id, 'negativo')}
                      title="Não útil"
                    >👎</button>
                  </div>
                </div>
              )
            })}
          </div>

          {totalPages > 1 && (
            <div className="feed-pagination">
              <button className="pagination-btn" disabled={page <= 1} onClick={() => loadFeed(page - 1)}>
                Anterior
              </button>
              <span className="pagination-info">{page} / {totalPages}</span>
              <button className="pagination-btn" disabled={page >= totalPages} onClick={() => loadFeed(page + 1)}>
                Próxima
              </button>
            </div>
          )}
        </main>
      </div>

      {modalItem && (
        <div className="modal-overlay" onClick={() => setModalItem(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <button className="modal-close" onClick={() => setModalItem(null)}>✕</button>
            <span className="feed-category">{modalItem.categoria}</span>
            <h2 className="modal-title">{modalItem.titulo}</h2>
            <p className="modal-meta">
              {modalItem.fonte} · {new Date(modalItem.data_publicacao).toLocaleDateString('pt-BR')}
            </p>
            {modalItem.resumo && <p className="modal-body">{modalItem.resumo}</p>}
            {modalItem.motivo && <p className="feed-reason">{modalItem.motivo}</p>}
          </div>
        </div>
      )}
    </div>
  )
}
