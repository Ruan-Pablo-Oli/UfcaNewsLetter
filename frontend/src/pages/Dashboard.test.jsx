import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'

import { Dashboard } from './Dashboard'
import { api } from '../api'

vi.mock('../api', () => ({
  api: { get: vi.fn(), post: vi.fn() },
}))

vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({ user: { username: 'aluno' }, logout: vi.fn() }),
}))

function conteudo(id, extra = {}) {
  return {
    id,
    titulo: `Conteúdo ${id}`,
    resumo: `Resumo do conteúdo ${id}`,
    categoria: 'edital',
    fonte: 'Portal UFCA',
    data_publicacao: '2026-07-20T12:00:00Z',
    universal: false,
    motivo: 'Você segue o interesse Editais',
    ...extra,
  }
}

function pagina(results, { page = 1, total_pages = 1 } = {}) {
  return { count: results.length, page, page_size: 20, total_pages, results }
}

function renderDashboard() {
  return render(
    <MemoryRouter>
      <Dashboard />
    </MemoryRouter>
  )
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('Dashboard — feed', () => {
  it('lista os conteúdos retornados por GET /feed', async () => {
    api.get.mockResolvedValue(pagina([conteudo(1), conteudo(2)]))

    renderDashboard()

    expect(await screen.findByText('Conteúdo 1')).toBeInTheDocument()
    expect(screen.getByText('Conteúdo 2')).toBeInTheDocument()
    expect(api.get).toHaveBeenCalledWith('/feed/?page=1&page_size=20')
  })

  it('exibe estado vazio quando o perfil não tem conteúdo correspondente', async () => {
    api.get.mockResolvedValue(pagina([]))

    renderDashboard()

    expect(
      await screen.findByText(/Ainda não há conteúdos no seu feed/)
    ).toBeInTheDocument()
  })

  it('mantém o feed vazio sem quebrar quando a API falha', async () => {
    api.get.mockRejectedValue(new Error('500'))

    renderDashboard()

    expect(
      await screen.findByText(/Ainda não há conteúdos no seu feed/)
    ).toBeInTheDocument()
  })
})

describe('Dashboard — paginação', () => {
  it('não exibe controles quando só há uma página', async () => {
    api.get.mockResolvedValue(pagina([conteudo(1)]))

    renderDashboard()
    await screen.findByText('Conteúdo 1')

    expect(screen.queryByRole('button', { name: 'Próxima' })).not.toBeInTheDocument()
  })

  it('carrega a página seguinte pela API ao clicar em Próxima', async () => {
    api.get
      .mockResolvedValueOnce(pagina([conteudo(1)], { page: 1, total_pages: 2 }))
      .mockResolvedValueOnce(pagina([conteudo(21)], { page: 2, total_pages: 2 }))

    renderDashboard()
    await screen.findByText('Conteúdo 1')

    expect(screen.getByRole('button', { name: 'Anterior' })).toBeDisabled()
    await userEvent.click(screen.getByRole('button', { name: 'Próxima' }))

    expect(api.get).toHaveBeenLastCalledWith('/feed/?page=2&page_size=20')
    expect(await screen.findByText('Conteúdo 21')).toBeInTheDocument()
    expect(screen.getByText('2 / 2')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Próxima' })).toBeDisabled()
  })
})

describe('Dashboard — tooltip "por que estou vendo isso?"', () => {
  it('revela a razão da recomendação ao clicar, sem abrir o modal do conteúdo', async () => {
    api.get.mockResolvedValue(pagina([conteudo(1)]))

    renderDashboard()
    await screen.findByText('Conteúdo 1')

    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument()

    await userEvent.click(
      screen.getByRole('button', { name: 'Por que estou vendo isso?' })
    )

    expect(screen.getByRole('tooltip')).toHaveTextContent(
      'Você segue o interesse Editais'
    )
    // O card inteiro é clicável: o clique no gatilho não pode abrir o modal.
    expect(
      screen.queryByRole('heading', { level: 2, name: 'Conteúdo 1' })
    ).not.toBeInTheDocument()
  })

  it('não renderiza o gatilho quando a API não envia motivo', async () => {
    api.get.mockResolvedValue(pagina([conteudo(1, { motivo: '' })]))

    renderDashboard()
    await screen.findByText('Conteúdo 1')

    expect(
      screen.queryByRole('button', { name: 'Por que estou vendo isso?' })
    ).not.toBeInTheDocument()
  })
})

describe('Dashboard — filtro local', () => {
  it('filtra os itens já carregados e explica que o filtro é só da página', async () => {
    api.get.mockResolvedValue(
      pagina([conteudo(1, { titulo: 'Edital de Monitoria' }), conteudo(2)])
    )

    renderDashboard()
    await screen.findByText('Edital de Monitoria')

    await userEvent.type(
      screen.getByLabelText('Filtrar os conteúdos desta página'),
      'monitoria'
    )

    expect(screen.getByText('Edital de Monitoria')).toBeInTheDocument()
    expect(screen.queryByText('Conteúdo 2')).not.toBeInTheDocument()

    await userEvent.clear(screen.getByLabelText('Filtrar os conteúdos desta página'))
    await userEvent.type(
      screen.getByLabelText('Filtrar os conteúdos desta página'),
      'inexistente'
    )

    expect(screen.getByText(/Nenhum resultado nesta página/)).toBeInTheDocument()
  })
})

describe('Dashboard — feedback de relevância', () => {
  it('envia o feedback positivo para a API', async () => {
    api.get.mockResolvedValue(pagina([conteudo(7)]))
    api.post.mockResolvedValue({})

    renderDashboard()
    await screen.findByText('Conteúdo 7')

    await userEvent.click(
      screen.getByRole('button', { name: 'Marcar "Conteúdo 7" como útil' })
    )

    expect(api.post).toHaveBeenCalledWith('/feedback/', {
      conteudo_id: 7,
      tipo: 'positivo',
    })
    expect(
      screen.getByRole('button', { name: 'Marcar "Conteúdo 7" como útil' })
    ).toHaveAttribute('aria-pressed', 'true')
  })
})
