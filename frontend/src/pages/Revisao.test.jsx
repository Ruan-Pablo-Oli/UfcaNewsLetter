import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { Revisao } from './Revisao'
import { api } from '../api'

vi.mock('../api', () => ({
  api: { get: vi.fn(), post: vi.fn() },
}))

vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({
    user: { username: 'admin', is_staff: true },
    logout: vi.fn(),
  }),
}))

function item(id, extra = {}) {
  return {
    id,
    titulo: `Pendente ${id}`,
    resumo: `Trecho do conteúdo ${id}`,
    categoria: null,
    categoria_nome: null,
    cursos: [],
    fonte_id: 1,
    fonte_nome: 'Informes — Editais',
    url: `https://www.ufca.edu.br/informes/pendente-${id}/`,
    data_publicacao: '2026-08-01T10:00:00Z',
    criado_em: '2026-08-02T10:00:00Z',
    ...extra,
  }
}

function renderRevisao() {
  return render(
    <MemoryRouter>
      <Revisao />
    </MemoryRouter>
  )
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('Revisão — fila', () => {
  it('lista os pendentes com o texto para o revisor decidir', async () => {
    api.get.mockResolvedValue({ itens: [item(1), item(2)], total: 2 })

    renderRevisao()

    expect(await screen.findByText('Pendente 1')).toBeInTheDocument()
    expect(screen.getByText('Trecho do conteúdo 1')).toBeInTheDocument()
    expect(screen.getByText(/2 conteúdo\(s\) aguardando revisão/)).toBeInTheDocument()
    expect(api.get).toHaveBeenCalledWith('/revisao/')
  })

  it('mostra estado vazio quando não há pendências', async () => {
    api.get.mockResolvedValue({ itens: [], total: 0 })

    renderRevisao()

    expect(await screen.findByText(/toda a fila foi revisada/)).toBeInTheDocument()
  })

  it('avisa sem quebrar quando a API falha', async () => {
    api.get.mockRejectedValue(new Error('500'))

    renderRevisao()

    expect(await screen.findByRole('alert')).toHaveTextContent(/Não foi possível carregar/)
  })

  it('marca visualmente o que está sem categoria', async () => {
    api.get.mockResolvedValue({ itens: [item(1)], total: 1 })

    renderRevisao()

    expect(await screen.findByText('sem categoria')).toBeInTheDocument()
  })
})

describe('Revisão — ações', () => {
  it('aprova enviando a categoria escolhida e tira o item da fila', async () => {
    api.get.mockResolvedValue({ itens: [item(1)], total: 1 })
    api.post.mockResolvedValue({ id: 1, status: 'aprovado' })

    renderRevisao()
    await screen.findByText('Pendente 1')

    await userEvent.selectOptions(screen.getByLabelText(/Categoria/), 'evento')
    await userEvent.click(screen.getByRole('button', { name: 'Aprovar' }))

    expect(api.post).toHaveBeenCalledWith('/revisao/1/aprovar/', { categoria: 'evento' })
    await waitFor(() => expect(screen.queryByText('Pendente 1')).toBeNull())
    expect(screen.getByRole('status')).toHaveTextContent('Conteúdo aprovado.')
  })

  it('aprova sem categoria quando o revisor não escolhe nenhuma', async () => {
    api.get.mockResolvedValue({ itens: [item(1)], total: 1 })
    api.post.mockResolvedValue({ id: 1, status: 'aprovado' })

    renderRevisao()
    await screen.findByText('Pendente 1')
    await userEvent.click(screen.getByRole('button', { name: 'Aprovar' }))

    expect(api.post).toHaveBeenCalledWith('/revisao/1/aprovar/', {})
  })

  it('descarta o conteúdo e o remove da lista', async () => {
    api.get.mockResolvedValue({ itens: [item(1)], total: 1 })
    api.post.mockResolvedValue({ id: 1, status: 'descartado' })

    renderRevisao()
    await screen.findByText('Pendente 1')
    await userEvent.click(screen.getByRole('button', { name: 'Descartar' }))

    expect(api.post).toHaveBeenCalledWith('/revisao/1/descartar/', {})
    await waitFor(() => expect(screen.queryByText('Pendente 1')).toBeNull())
  })

  it('recarrega a fila ao reclassificar, já que o item pode continuar pendente', async () => {
    api.get.mockResolvedValue({ itens: [item(1)], total: 1 })
    api.post.mockResolvedValue({ id: 1, categoria: 'edital' })

    renderRevisao()
    await screen.findByText('Pendente 1')
    await userEvent.click(screen.getByRole('button', { name: 'Reclassificar' }))

    expect(api.post).toHaveBeenCalledWith('/revisao/1/reclassificar/', {})
    await waitFor(() => expect(api.get).toHaveBeenCalledTimes(2))
  })

  it('mantém o item na fila e avisa quando a ação falha', async () => {
    api.get.mockResolvedValue({ itens: [item(1)], total: 1 })
    api.post.mockRejectedValue(new Error('categoria inválida'))

    renderRevisao()
    await screen.findByText('Pendente 1')
    await userEvent.click(screen.getByRole('button', { name: 'Aprovar' }))

    expect(await screen.findByRole('status')).toHaveTextContent('categoria inválida')
    expect(screen.getByText('Pendente 1')).toBeInTheDocument()
  })
})
