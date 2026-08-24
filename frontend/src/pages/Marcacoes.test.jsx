import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { Marcacoes } from './Marcacoes'
import { api } from '../api'

vi.mock('../api', () => ({
  api: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}))

vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({ user: { username: 'aluno' }, logout: vi.fn() }),
}))

function marcacao(id, extra = {}) {
  return {
    id,
    conteudo_id: 100 + id,
    conteudo_titulo: `Conteúdo ${id}`,
    conteudo_resumo: `Resumo ${id}`,
    conteudo_url: `https://www.ufca.edu.br/informes/conteudo-${id}/`,
    categoria: 'edital',
    fonte: 'Portal UFCA',
    tipo: 'negativo',
    criado_em: '2026-08-20T10:00:00Z',
    ...extra,
  }
}

function pagina(results) {
  return { count: results.length, page: 1, page_size: 50, total_pages: 1, results }
}

function renderMarcacoes() {
  return render(
    <MemoryRouter>
      <Marcacoes />
    </MemoryRouter>
  )
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('Marcações — listagem', () => {
  it('abre nos irrelevantes e pede só os negativos à API', async () => {
    api.get.mockResolvedValue(pagina([marcacao(1)]))

    renderMarcacoes()

    expect(await screen.findByText('Conteúdo 1')).toBeInTheDocument()
    expect(api.get).toHaveBeenCalledWith('/feedback/historico/?tipo=negativo&page_size=50')
  })

  it('troca para os úteis ao clicar na aba', async () => {
    api.get.mockResolvedValue(pagina([]))

    renderMarcacoes()
    await screen.findByText(/não marcou nenhum conteúdo como irrelevante/)

    await userEvent.click(screen.getByRole('tab', { name: 'Úteis' }))

    await waitFor(() =>
      expect(api.get).toHaveBeenLastCalledWith(
        '/feedback/historico/?tipo=positivo&page_size=50'
      )
    )
    expect(await screen.findByText(/ainda não marcou nenhum conteúdo como útil/)).toBeInTheDocument()
  })

  it('mostra o erro da API sem quebrar a tela', async () => {
    api.get.mockRejectedValue(new Error('Sua sessão expirou. Entre novamente.'))

    renderMarcacoes()

    expect(await screen.findByRole('alert')).toHaveTextContent(/sessão expirou/)
  })
})

describe('Marcações — desfazer', () => {
  it('apaga a marcação e explica que o conteúdo volta ao feed', async () => {
    api.get.mockResolvedValue(pagina([marcacao(1)]))
    api.delete.mockResolvedValue({ conteudo_id: 101, removido: true })

    renderMarcacoes()
    await screen.findByText('Conteúdo 1')

    await userEvent.click(screen.getByRole('button', { name: /Desfazer marcação/ }))

    expect(api.delete).toHaveBeenCalledWith('/feedback/101/')
    await waitFor(() => expect(screen.queryByText('Conteúdo 1')).toBeNull())
    expect(screen.getByRole('status')).toHaveTextContent(/volta a aparecer no seu feed/)
  })

  it('mantém o item e avisa quando desfazer falha', async () => {
    api.get.mockResolvedValue(pagina([marcacao(1)]))
    api.delete.mockRejectedValue(new Error('Marcação não encontrada.'))

    renderMarcacoes()
    await screen.findByText('Conteúdo 1')

    await userEvent.click(screen.getByRole('button', { name: /Desfazer marcação/ }))

    expect(await screen.findByRole('status')).toHaveTextContent('Marcação não encontrada.')
    expect(screen.getByText('Conteúdo 1')).toBeInTheDocument()
  })
})
