import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { api } from '../api'
import { Esqueleto } from '../components/Esqueleto'

// Só os tipos com coletor implementado coletam de fato; `pdf` existe no modelo
// mas o orquestrador o pula, então avisamos em vez de deixar cadastrar às cegas.
const TIPOS = [
  { valor: 'html', rotulo: 'HTML (notícias e informes)', coleta: true },
  { valor: 'calendario', rotulo: 'Calendário e eventos', coleta: true },
  { valor: 'concurso', rotulo: 'Concursos e seleções', coleta: true },
  { valor: 'pdf', rotulo: 'PDF (sem coletor)', coleta: false },
]

const NOVA_FONTE = { nome: '', tipo: 'html', url: '', intervalo_coleta: 60 }

function formatarData(iso) {
  return iso ? new Date(iso).toLocaleString('pt-BR') : 'nunca coletada'
}

/** Painel de fontes (US-05.1). Restrito a staff — ver ProtectedRoute. */
export function Fontes() {
  const { user, logout } = useAuth()
  const [fontes, setFontes] = useState([])
  const [carregando, setCarregando] = useState(true)
  const [erro, setErro] = useState('')
  const [aviso, setAviso] = useState('')
  const [nova, setNova] = useState(NOVA_FONTE)
  const [salvando, setSalvando] = useState(false)
  const [emAcao, setEmAcao] = useState(null)

  const carregar = useCallback(async () => {
    try {
      const dados = await api.get('/fontes/')
      setFontes(dados.fontes)
      setErro('')
    } catch (e) {
      setErro(e.message || 'Não foi possível carregar as fontes.')
      setFontes([])
    } finally {
      setCarregando(false)
    }
  }, [])

  // Mesmo caso do Dashboard: nada é atualizado de forma síncrona aqui.
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { carregar() }, [carregar])

  async function criar(evento) {
    evento.preventDefault()
    setSalvando(true)
    setAviso('')
    try {
      const criada = await api.post('/fontes/criar/', {
        ...nova,
        intervalo_coleta: Number(nova.intervalo_coleta),
      })
      setFontes((atuais) => [...atuais, criada])
      setNova(NOVA_FONTE)
      setAviso(`Fonte "${criada.nome}" cadastrada.`)
    } catch (e) {
      setAviso(e.message || 'Não foi possível cadastrar a fonte.')
    } finally {
      setSalvando(false)
    }
  }

  async function alternarAtivo(fonte) {
    setEmAcao(fonte.id)
    setAviso('')
    try {
      const atualizada = await api.patch(`/fontes/${fonte.id}/`, { ativo: !fonte.ativo })
      setFontes((atuais) => atuais.map((f) => (f.id === fonte.id ? atualizada : f)))
      setAviso(
        atualizada.ativo
          ? `"${atualizada.nome}" será coletada no próximo ciclo.`
          : `"${atualizada.nome}" não será mais coletada.`
      )
    } catch (e) {
      setAviso(e.message || 'Não foi possível alterar a fonte.')
    } finally {
      setEmAcao(null)
    }
  }

  async function alterarIntervalo(fonte, minutos) {
    const intervalo = Number(minutos)
    if (!Number.isInteger(intervalo) || intervalo <= 0) {
      setAviso('O intervalo deve ser um número inteiro de minutos, maior que zero.')
      return
    }
    if (intervalo === fonte.intervalo_coleta) return

    setEmAcao(fonte.id)
    try {
      const atualizada = await api.patch(`/fontes/${fonte.id}/`, {
        intervalo_coleta: intervalo,
      })
      setFontes((atuais) => atuais.map((f) => (f.id === fonte.id ? atualizada : f)))
      setAviso(`Intervalo de "${atualizada.nome}" agora é de ${intervalo} min.`)
    } catch (e) {
      setAviso(e.message || 'Não foi possível alterar o intervalo.')
    } finally {
      setEmAcao(null)
    }
  }

  async function remover(fonte) {
    setEmAcao(fonte.id)
    setAviso('')
    try {
      await api.delete(`/fontes/${fonte.id}/remover/`)
      setFontes((atuais) => atuais.filter((f) => f.id !== fonte.id))
      setAviso(`Fonte "${fonte.nome}" removida.`)
    } catch (e) {
      // O backend recusa remover fonte com conteúdo (PROTECT) e sugere desativar.
      setAviso(e.message || 'Não foi possível remover a fonte.')
    } finally {
      setEmAcao(null)
    }
  }

  const semColetor = TIPOS.find((t) => t.valor === nova.tipo && !t.coleta)

  return (
    <div className="page">
      <header className="revisao-topo">
        <Link to="/" className="revisao-voltar">← Voltar ao feed</Link>
        <span className="revisao-usuario">{user?.username}</span>
        <button className="revisao-sair" onClick={logout}>Sair</button>
      </header>

      <main className="revisao">
        <h1 className="revisao-title">Fontes de conteúdo</h1>
        <p className="revisao-intro">
          O coletor varre as fontes ativas respeitando o intervalo de cada uma.
          Alterações valem já no próximo ciclo do agendador, sem reiniciar nada.
        </p>

        {aviso && <div className="revisao-aviso" role="status">{aviso}</div>}
        {erro && <div className="revisao-erro" role="alert">{erro}</div>}

        <form className="fonte-form" onSubmit={criar}>
          <h2 className="fonte-form-titulo">Nova fonte</h2>
          <div className="fonte-form-linha">
            <label>
              Nome
              <input
                value={nova.nome}
                onChange={(e) => setNova({ ...nova, nome: e.target.value })}
                placeholder="Informes — Extensão"
                required
              />
            </label>
            <label>
              Tipo
              <select
                value={nova.tipo}
                onChange={(e) => setNova({ ...nova, tipo: e.target.value })}
              >
                {TIPOS.map((t) => (
                  <option key={t.valor} value={t.valor}>{t.rotulo}</option>
                ))}
              </select>
            </label>
            <label>
              Intervalo (min)
              <input
                type="number"
                min="1"
                value={nova.intervalo_coleta}
                onChange={(e) => setNova({ ...nova, intervalo_coleta: e.target.value })}
              />
            </label>
          </div>
          <label className="fonte-form-url">
            URL
            <input
              type="url"
              value={nova.url}
              onChange={(e) => setNova({ ...nova, url: e.target.value })}
              placeholder="https://www.ufca.edu.br/noticias/"
              required
            />
          </label>
          {semColetor && (
            <p className="fonte-alerta">
              Esse tipo ainda não tem coletor implementado: a fonte fica cadastrada,
              mas é pulada em toda coleta.
            </p>
          )}
          <button className="revisao-btn aprovar" disabled={salvando}>
            {salvando ? 'Cadastrando…' : 'Cadastrar fonte'}
          </button>
        </form>

        {carregando ? (
          <Esqueleto linhas={3} />
        ) : fontes.length === 0 ? (
          <p className="revisao-vazio">Nenhuma fonte cadastrada.</p>
        ) : (
          <ul className="revisao-lista">
            {fontes.map((fonte) => (
              <li key={fonte.id} className="revisao-item">
                <div className="revisao-meta">
                  <span className="revisao-categoria">{fonte.tipo}</span>
                  <span
                    className={`fonte-estado ${fonte.ativo ? 'ativa' : 'inativa'}`}
                  >
                    {fonte.ativo ? 'ativa' : 'inativa'}
                  </span>
                  <span className="revisao-data">
                    Última coleta: {formatarData(fonte.ultima_coleta)}
                  </span>
                </div>

                <h2 className="revisao-item-titulo">{fonte.nome}</h2>
                <a
                  className="revisao-link"
                  href={fonte.url}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {fonte.url}
                </a>

                <div className="revisao-acoes">
                  <label className="revisao-select-label">
                    Intervalo (min)
                    <input
                      type="number"
                      min="1"
                      defaultValue={fonte.intervalo_coleta}
                      disabled={emAcao === fonte.id}
                      onBlur={(e) => alterarIntervalo(fonte, e.target.value)}
                      aria-label={`Intervalo de coleta de ${fonte.nome}`}
                    />
                  </label>
                  <button
                    className={`revisao-btn ${fonte.ativo ? 'descartar' : 'aprovar'}`}
                    disabled={emAcao === fonte.id}
                    onClick={() => alternarAtivo(fonte)}
                  >
                    {fonte.ativo ? 'Desativar' : 'Ativar'}
                  </button>
                  <button
                    className="revisao-btn reclassificar"
                    disabled={emAcao === fonte.id}
                    onClick={() => remover(fonte)}
                    title="Só é possível remover fontes sem conteúdo coletado"
                  >
                    Remover
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
