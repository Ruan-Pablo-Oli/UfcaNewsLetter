import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { api, ApiError, EVENTO_SESSAO_EXPIRADA } from './api'

function resposta(body, { status = 200, json = true, redirected = false, url = '/x' } = {}) {
  return {
    ok: status >= 200 && status < 300,
    status,
    redirected,
    url,
    headers: {
      get: () => (json ? 'application/json' : 'text/html; charset=utf-8'),
    },
    json: async () => {
      if (!json) throw new SyntaxError('Unexpected token < in JSON at position 0')
      return body
    },
  }
}

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn())
  document.cookie = 'csrftoken=token-de-teste'
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('api — respostas que não são JSON', () => {
  it('não vaza SyntaxError quando o servidor devolve HTML', async () => {
    fetch.mockResolvedValue(resposta('<!doctype html>', { json: false }))

    await expect(api.get('/feed/')).rejects.toThrow(/formato inesperado/)
    // O erro que aparecia antes: "JSON.parse: unexpected character…"
    await expect(api.get('/feed/')).rejects.not.toThrow(/JSON/)
  })

  it('traduz o redirecionamento para o login em sessão expirada', async () => {
    fetch.mockResolvedValue(
      resposta('<!doctype html>', {
        json: false,
        redirected: true,
        url: 'http://localhost:8000/accounts/login/?next=/revisao/1/aprovar/',
      })
    )

    const erro = await api.post('/revisao/1/aprovar/', {}).catch((e) => e)

    expect(erro).toBeInstanceOf(ApiError)
    expect(erro.sessaoExpirada).toBe(true)
    expect(erro.message).toMatch(/sessão expirou/i)
  })

  it('avisa o app quando a sessão cai, para o login ser retomado', async () => {
    const ouvinte = vi.fn()
    window.addEventListener(EVENTO_SESSAO_EXPIRADA, ouvinte)
    fetch.mockResolvedValue(resposta({ erro: 'Não autenticado.' }, { status: 401 }))

    await api.get('/accounts/api/me/').catch(() => {})

    expect(ouvinte).toHaveBeenCalled()
    window.removeEventListener(EVENTO_SESSAO_EXPIRADA, ouvinte)
  })

  it('explica a falha de rede em vez de estourar o erro do fetch', async () => {
    fetch.mockRejectedValue(new TypeError('NetworkError when attempting to fetch'))

    await expect(api.get('/feed/')).rejects.toThrow(/falar com o servidor/)
  })
})

describe('api — mensagens de erro', () => {
  it('usa a mensagem enviada pelo backend', async () => {
    fetch.mockResolvedValue(resposta({ erro: 'categoria inválida' }, { status: 400 }))

    await expect(api.post('/revisao/1/aprovar/', {})).rejects.toThrow('categoria inválida')
  })

  it('usa a primeira mensagem quando o erro vem por campo do formulário', async () => {
    fetch.mockResolvedValue(
      resposta({ erro: { curso: 'Selecione um curso.' } }, { status: 400 })
    )

    await expect(api.patch('/accounts/api/perfil/', {})).rejects.toThrow('Selecione um curso.')
  })

  it('tem mensagem própria para 403 sem corpo em JSON', async () => {
    fetch.mockResolvedValue(resposta(null, { status: 403, json: false }))

    await expect(api.post('/revisao/1/aprovar/', {})).rejects.toThrow(/não tem permissão/i)
  })

  it('devolve os dados quando a resposta é JSON válido', async () => {
    fetch.mockResolvedValue(resposta({ count: 2, results: [] }))

    await expect(api.get('/feed/')).resolves.toEqual({ count: 2, results: [] })
  })
})
