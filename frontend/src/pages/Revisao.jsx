import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { api } from '../api'

const CATEGORIAS = [
  { valor: 'edital', rotulo: 'Edital' },
  { valor: 'comunicado', rotulo: 'Comunicado' },
  { valor: 'evento', rotulo: 'Evento' },
  { valor: 'prazo', rotulo: 'Prazo' },
]

/** Fila de revisão manual (US-05.2). Só staff chega aqui — ver ProtectedRoute. */
export function Revisao() {
  const { user, logout } = useAuth()
  const [itens, setItens] = useState([])
  const [total, setTotal] = useState(0)
  const [carregando, setCarregando] = useState(true)
  const [erro, setErro] = useState('')
  // Categoria escolhida por item antes de aprovar, por id.
  const [categorias, setCategorias] = useState({})
  // Item cuja ação está em curso, para desabilitar os botões dele.
  const [emAcao, setEmAcao] = useState(null)
  const [aviso, setAviso] = useState('')

  // Nenhuma atualização de estado acontece de forma síncrona aqui: todas vêm
  // depois do `await`, quando a resposta de GET /revisao/ chega. É busca de
  // dados na montagem, não render em cascata.
  const carregar = useCallback(async () => {
    try {
      const dados = await api.get('/revisao/')
      setItens(dados.itens)
      setTotal(dados.total)
      setErro('')
    } catch {
      setErro('Não foi possível carregar a fila de revisão.')
      setItens([])
    } finally {
      setCarregando(false)
    }
  }, [])

  // Mesmo caso do Dashboard: a regra não distingue "setState depois do await"
  // de render em cascata.
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { carregar() }, [carregar])

  async function agir(item, acao) {
    setEmAcao(item.id)
    setAviso('')
    try {
      const corpo =
        acao === 'aprovar' && categorias[item.id] ? { categoria: categorias[item.id] } : {}
      await api.post(`/revisao/${item.id}/${acao}/`, corpo)
      // Some da fila: aprovado e descartado saem de status=pendente; o
      // reclassificar pode ou não resolver, então recarregamos a lista.
      if (acao === 'reclassificar') {
        await carregar()
        setAviso('Classificador reaplicado.')
      } else {
        setItens((atuais) => atuais.filter((i) => i.id !== item.id))
        setTotal((n) => Math.max(0, n - 1))
        setAviso(acao === 'aprovar' ? 'Conteúdo aprovado.' : 'Conteúdo descartado.')
      }
    } catch (e) {
      setAviso(e.message || 'A ação falhou.')
    } finally {
      setEmAcao(null)
    }
  }

  return (
    <div className="page">
      <header className="revisao-topo">
        <Link to="/" className="revisao-voltar">← Voltar ao feed</Link>
        <span className="revisao-usuario">{user?.username}</span>
        <button className="revisao-sair" onClick={logout}>Sair</button>
      </header>

      <main className="revisao">
        <h1 className="revisao-title">Fila de revisão</h1>
        <p className="revisao-intro">
          Conteúdo coletado que o classificador não conseguiu categorizar. Aprovar
          publica no feed dos estudantes; descartar mantém fora.
        </p>

        {aviso && <div className="revisao-aviso" role="status">{aviso}</div>}
        {erro && <div className="revisao-erro" role="alert">{erro}</div>}

        {carregando ? (
          <p className="revisao-vazio">Carregando…</p>
        ) : itens.length === 0 ? (
          <p className="revisao-vazio">
            Nada pendente — toda a fila foi revisada.
          </p>
        ) : (
          <>
            <p className="revisao-total">{total} conteúdo(s) aguardando revisão</p>
            <ul className="revisao-lista">
              {itens.map((item) => (
                <li key={item.id} className="revisao-item">
                  <div className="revisao-meta">
                    <span className="revisao-fonte">{item.fonte_nome}</span>
                    <span className="revisao-data">
                      {new Date(item.data_publicacao).toLocaleDateString('pt-BR')}
                    </span>
                    {item.categoria_nome ? (
                      <span className="revisao-categoria">{item.categoria_nome}</span>
                    ) : (
                      <span className="revisao-categoria revisao-categoria-vazia">
                        sem categoria
                      </span>
                    )}
                  </div>

                  <h2 className="revisao-item-titulo">{item.titulo}</h2>
                  {item.resumo && <p className="revisao-resumo">{item.resumo}</p>}
                  {item.url && (
                    <a
                      className="revisao-link"
                      href={item.url}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      Abrir original ↗
                    </a>
                  )}

                  <div className="revisao-acoes">
                    <label className="revisao-select-label">
                      Categoria
                      <select
                        value={categorias[item.id] || item.categoria_nome || ''}
                        onChange={(e) =>
                          setCategorias((c) => ({ ...c, [item.id]: e.target.value }))
                        }
                      >
                        <option value="">manter sem categoria</option>
                        {CATEGORIAS.map((c) => (
                          <option key={c.valor} value={c.valor}>{c.rotulo}</option>
                        ))}
                      </select>
                    </label>

                    <button
                      className="revisao-btn aprovar"
                      disabled={emAcao === item.id}
                      onClick={() => agir(item, 'aprovar')}
                    >
                      Aprovar
                    </button>
                    <button
                      className="revisao-btn descartar"
                      disabled={emAcao === item.id}
                      onClick={() => agir(item, 'descartar')}
                    >
                      Descartar
                    </button>
                    <button
                      className="revisao-btn reclassificar"
                      disabled={emAcao === item.id}
                      onClick={() => agir(item, 'reclassificar')}
                      title="Reaplica o classificador automático a este conteúdo"
                    >
                      Reclassificar
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          </>
        )}
      </main>
    </div>
  )
}
