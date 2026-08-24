/** Erro de chamada à API, com o status e a distinção de sessão expirada. */
export class ApiError extends Error {
  constructor(message, { status = 0, sessaoExpirada = false } = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.sessaoExpirada = sessaoExpirada
  }
}

/** Evento disparado quando a sessão cai; o AuthProvider escuta e desloga. */
export const EVENTO_SESSAO_EXPIRADA = 'ufca:sessao-expirada'

function getCSRFToken() {
  const name = 'csrftoken'
  const value = `; ${document.cookie}`
  const parts = value.split(`; ${name}=`)
  if (parts.length === 2) return parts.pop().split(';').shift()
  return ''
}

/**
 * Detecta a resposta da tela de login.
 *
 * As rotas protegidas do Django redirecionam para `/accounts/login/` quando a
 * sessão cai ou o usuário não tem permissão. O `fetch` segue o redirect e
 * entrega o HTML da tela de login **com status 200** — então `response.ok` é
 * verdadeiro e o corpo não é JSON. Sem tratar esse caso, a tela mostrava
 * "JSON.parse: unexpected character", que não diz nada a quem só precisa
 * entrar de novo.
 */
function respostaDeLogin(response) {
  return response.redirected && response.url.includes('/accounts/login')
}

/** Lê o corpo como JSON; devolve null quando não é JSON (HTML de erro, vazio). */
async function lerJson(response) {
  const tipo = response.headers.get('content-type') || ''
  if (!tipo.includes('application/json')) return null
  try {
    return await response.json()
  } catch {
    // Content-Type diz JSON mas o corpo está truncado ou vazio (204, proxy).
    return null
  }
}

function mensagemDeErro(data, status) {
  const erro = data?.erro
  if (typeof erro === 'string') return erro
  // Erros de formulário chegam como {campo: mensagem}; mostramos a primeira.
  if (erro && typeof erro === 'object') return Object.values(erro)[0]
  if (status === 403) return 'Você não tem permissão para esta ação.'
  if (status === 404) return 'Conteúdo não encontrado.'
  if (status >= 500) return 'O servidor falhou ao processar a solicitação.'
  return `Erro ${status}`
}

async function request(endpoint, options = {}) {
  const config = {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  }

  if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(options.method?.toUpperCase())) {
    config.headers['X-CSRFToken'] = getCSRFToken()
  }

  if (config.body && typeof config.body === 'object') {
    config.body = JSON.stringify(config.body)
  }

  let response
  try {
    response = await fetch(endpoint, config)
  } catch {
    // Rede fora, servidor derrubado, DNS: o fetch rejeita antes de haver resposta.
    throw new ApiError('Não foi possível falar com o servidor. Verifique sua conexão.')
  }

  if (respostaDeLogin(response) || response.status === 401) {
    // Avisa o app inteiro de uma vez, em vez de cada tela adivinhar.
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent(EVENTO_SESSAO_EXPIRADA))
    }
    throw new ApiError('Sua sessão expirou. Entre novamente.', {
      status: 401,
      sessaoExpirada: true,
    })
  }

  const data = await lerJson(response)

  if (!response.ok) {
    throw new ApiError(mensagemDeErro(data, response.status), { status: response.status })
  }

  if (data === null) {
    throw new ApiError(
      'O servidor respondeu em um formato inesperado.',
      { status: response.status },
    )
  }

  return data
}

export const api = {
  get: (url) => request(url, { method: 'GET' }),
  post: (url, body) => request(url, { method: 'POST', body }),
  patch: (url, body) => request(url, { method: 'PATCH', body }),
  delete: (url, body) => request(url, { method: 'DELETE', body }),
}
