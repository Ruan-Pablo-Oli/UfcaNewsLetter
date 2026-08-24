import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { api } from '../api'

const ABAS = [
  { tipo: 'negativo', rotulo: 'Irrelevantes', vazio: 'Você não marcou nenhum conteúdo como irrelevante.' },
  { tipo: 'positivo', rotulo: 'Úteis', vazio: 'Você ainda não marcou nenhum conteúdo como útil.' },
]

/** Marcações de relevância do estudante, com a opção de desfazer (US-01.3). */
export function Marcacoes() {
  const { user, logout } = useAuth()
  const [aba, setAba] = useState('negativo')
  const [itens, setItens] = useState([])
  const [carregando, setCarregando] = useState(true)
  const [erro, setErro] = useState('')
  const [aviso, setAviso] = useState('')
  const [emAcao, setEmAcao] = useState(null)

  const carregar = useCallback(async (tipo) => {
    try {
      const dados = await api.get(`/feedback/historico/?tipo=${tipo}&page_size=50`)
      setItens(dados.results)
      setErro('')
    } catch (e) {
      setErro(e.message || 'Não foi possível carregar suas marcações.')
      setItens([])
    } finally {
      setCarregando(false)
    }
  }, [])

  // Nada é atualizado de forma síncrona: tudo acontece depois do await.
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { carregar(aba) }, [carregar, aba])

  async function desfazer(item) {
    setEmAcao(item.conteudo_id)
    setAviso('')
    try {
      await api.delete(`/feedback/${item.conteudo_id}/`)
      setItens((atuais) => atuais.filter((i) => i.conteudo_id !== item.conteudo_id))
      setAviso(
        aba === 'negativo'
          ? 'Marcação desfeita — o conteúdo volta a aparecer no seu feed.'
          : 'Marcação desfeita.'
      )
    } catch (e) {
      setAviso(e.message || 'Não foi possível desfazer a marcação.')
    } finally {
      setEmAcao(null)
    }
  }

  function trocarAba(tipo) {
    setAba(tipo)
    setCarregando(true)
    setAviso('')
  }

  const abaAtual = ABAS.find((a) => a.tipo === aba)

  return (
    <div className="page">
      <header className="revisao-topo">
        <Link to="/" className="revisao-voltar">← Voltar ao feed</Link>
        <span className="revisao-usuario">{user?.username}</span>
        <button className="revisao-sair" onClick={logout}>Sair</button>
      </header>

      <main className="revisao">
        <h1 className="revisao-title">Minhas marcações</h1>
        <p className="revisao-intro">
          O que você marcou como irrelevante sai do seu feed e deixa de ser enviado
          por e-mail e notificação. Desfazer traz o conteúdo de volta — a marcação
          é só sua e não afeta outros estudantes.
        </p>

        <div className="marcacoes-abas" role="tablist">
          {ABAS.map((a) => (
            <button
              key={a.tipo}
              role="tab"
              aria-selected={aba === a.tipo}
              className={`marcacoes-aba ${aba === a.tipo ? 'ativa' : ''}`}
              onClick={() => trocarAba(a.tipo)}
            >
              {a.rotulo}
            </button>
          ))}
        </div>

        {aviso && <div className="revisao-aviso" role="status">{aviso}</div>}
        {erro && <div className="revisao-erro" role="alert">{erro}</div>}

        {carregando ? (
          <p className="revisao-vazio">Carregando…</p>
        ) : itens.length === 0 ? (
          <p className="revisao-vazio">{abaAtual.vazio}</p>
        ) : (
          <ul className="revisao-lista">
            {itens.map((item) => (
              <li key={item.id} className="revisao-item">
                <div className="revisao-meta">
                  {item.categoria && (
                    <span className="revisao-categoria">{item.categoria}</span>
                  )}
                  <span className="revisao-fonte">{item.fonte}</span>
                  <span className="revisao-data">
                    marcado em {new Date(item.criado_em).toLocaleDateString('pt-BR')}
                  </span>
                </div>

                <h2 className="revisao-item-titulo">{item.conteudo_titulo}</h2>
                {item.conteudo_resumo && (
                  <p className="revisao-resumo">{item.conteudo_resumo}</p>
                )}
                {item.conteudo_url && (
                  <a
                    className="revisao-link"
                    href={item.conteudo_url}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    Abrir no site da UFCA ↗
                  </a>
                )}

                <div className="revisao-acoes">
                  <button
                    className="revisao-btn aprovar"
                    disabled={emAcao === item.conteudo_id}
                    onClick={() => desfazer(item)}
                  >
                    Desfazer marcação
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </main>
    </div>
  )
}
