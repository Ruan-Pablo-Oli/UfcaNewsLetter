import { useState, useEffect, useMemo, useCallback } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { useNavigate, Link } from 'react-router-dom'
import { api } from '../api'
import { ReasonTooltip } from '../components/ReasonTooltip'

const UM_DIA = 24 * 60 * 60 * 1000

/** Prazo com urgência relativa: o que importa ao estudante é "faltam 3 dias". */
function PrazoBadge({ prazo }) {
  const data = new Date(prazo)
  if (Number.isNaN(data.getTime())) return null

  const hoje = new Date()
  const dias = Math.ceil((data - hoje) / UM_DIA)
  const formatada = data.toLocaleDateString('pt-BR')

  let urgencia = 'normal'
  let texto = `Prazo: ${formatada}`
  if (dias < 0) {
    urgencia = 'encerrado'
    texto = `Prazo encerrado em ${formatada}`
  } else if (dias === 0) {
    urgencia = 'hoje'
    texto = `Prazo termina hoje (${formatada})`
  } else if (dias <= 7) {
    urgencia = 'proximo'
    texto = `Faltam ${dias} dia${dias > 1 ? 's' : ''} — até ${formatada}`
  }

  return (
    <span className={`feed-prazo feed-prazo-${urgencia}`}>
      ⏳ {texto}
    </span>
  )
}

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

  const fetchFeed = useCallback(async (p) => {
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
  }, [])

  // A carga inicial não marca `loading`: o estado já nasce `true`. Marcar aqui
  // seria um setState síncrono dentro do efeito (cascading render).
  const loadFeed = useCallback((p) => {
    setLoading(true)
    return fetchFeed(p)
  }, [fetchFeed])

  // `set-state-in-effect` sinaliza qualquer setState alcançável pelo efeito,
  // inclusive depois do `await`. Aqui a atualização só ocorre quando a resposta
  // de `GET /feed/` chega — busca de dados na montagem, não render em cascata.
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { fetchFeed(1) }, [fetchFeed])

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
            <Link to="/busca" className="dashboard-nav-item">
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
            {/* Moderação é restrita a staff no backend; escondida para os demais. */}
            {user?.is_staff && (
              <Link to="/revisao" className="dashboard-nav-item">
                <span className="nav-icon">🛡️</span>
                Fila de revisão
              </Link>
            )}
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
            {/* Filtro local: age apenas sobre os itens já carregados nesta
                página. A busca em todo o feed é a US-07.1 (#28). */}
            <input
              type="text"
              className="feed-search"
              placeholder="Filtrar nesta página..."
              aria-label="Filtrar os conteúdos desta página"
              title="Filtra apenas os conteúdos já carregados nesta página"
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
              {search || filterCat ? (
                'Nenhum resultado nesta página. O filtro considera apenas os conteúdos já carregados.'
              ) : (
                <>
                  Ainda não há conteúdos no seu feed.{' '}
                  <Link to="/perfil">Complete seu perfil</Link> para receber notícias personalizadas.
                </>
              )}
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
                  {item.prazo && <PrazoBadge prazo={item.prazo} />}
                  {item.resumo && <p className="feed-summary">{item.resumo}</p>}
                  {item.url && (
                    <a
                      className="feed-link"
                      href={item.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      onClick={(e) => e.stopPropagation()}
                    >
                      Abrir no site da UFCA ↗
                    </a>
                  )}
                  <ReasonTooltip motivo={item.motivo} />
                  <div className="feed-actions" onClick={(e) => e.stopPropagation()}>
                    <button
                      className={`feed-btn like ${item.feedback === 'positivo' ? 'active' : ''}`}
                      onClick={() => handleFeedback(item.id, 'positivo')}
                      title="Útil"
                      aria-label={`Marcar "${item.titulo}" como útil`}
                      aria-pressed={item.feedback === 'positivo'}
                    >👍</button>
                    <button
                      className={`feed-btn dislike ${item.feedback === 'negativo' ? 'active' : ''}`}
                      onClick={() => handleFeedback(item.id, 'negativo')}
                      title="Não útil"
                      aria-label={`Marcar "${item.titulo}" como irrelevante`}
                      aria-pressed={item.feedback === 'negativo'}
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
            {modalItem.prazo && <PrazoBadge prazo={modalItem.prazo} />}
            {modalItem.resumo && <p className="modal-body">{modalItem.resumo}</p>}
            {modalItem.url && (
              <a
                className="modal-link"
                href={modalItem.url}
                target="_blank"
                rel="noopener noreferrer"
              >
                Abrir no site da UFCA ↗
              </a>
            )}
            {modalItem.motivo && <p className="modal-reason">{modalItem.motivo}</p>}
          </div>
        </div>
      )}
    </div>
  )
}
