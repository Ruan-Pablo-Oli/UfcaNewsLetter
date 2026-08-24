import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { Fontes } from './Fontes'
import { api } from '../api'

vi.mock('../api', () => ({
  api: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}))

vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({ user: { username: 'admin', is_staff: true }, logout: vi.fn() }),
}))

function fonte(id, extra = {}) {
  return {
    id,
    nome: `Fonte ${id}`,
    tipo: 'html',
    url: `https://www.ufca.edu.br/fonte-${id}/`,
    intervalo_coleta: 60,
    ativo: true,
    ultima_coleta: '2026-08-24T12:00:00Z',
    ...extra,
  }
}

function renderFontes() {
  return render(
    <MemoryRouter>
      <Fontes />
    </MemoryRouter>
  )
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('Fontes — listagem', () => {
  it('lista as fontes com estado e última coleta', async () => {
    api.get.mockResolvedValue({ fontes: [fonte(1), fonte(2, { ativo: false })] })

    renderFontes()

    expect(await screen.findByText('Fonte 1')).toBeInTheDocument()
    expect(screen.getByText('ativa')).toBeInTheDocument()
    expect(screen.getByText('inativa')).toBeInTheDocument()
    expect(api.get).toHaveBeenCalledWith('/fontes/')
  })

  it('deixa claro quando a fonte nunca foi coletada', async () => {
    api.get.mockResolvedValue({ fontes: [fonte(1, { ultima_coleta: null })] })

    renderFontes()

    expect(await screen.findByText(/nunca coletada/)).toBeInTheDocument()
  })

  it('mostra o erro da API sem quebrar a tela', async () => {
    api.get.mockRejectedValue(new Error('Sua sessão expirou. Entre novamente.'))

    renderFontes()

    expect(await screen.findByRole('alert')).toHaveTextContent(/sessão expirou/)
  })
})

describe('Fontes — cadastro', () => {
  it('cadastra uma fonte nova e a acrescenta à lista', async () => {
    api.get.mockResolvedValue({ fontes: [] })
    api.post.mockResolvedValue(fonte(9, { nome: 'Informes — Extensão' }))

    renderFontes()
    await screen.findByText(/Nenhuma fonte cadastrada/)

    await userEvent.type(screen.getByLabelText('Nome'), 'Informes — Extensão')
    await userEvent.type(
      screen.getByLabelText('URL'),
      'https://www.ufca.edu.br/informes/extensao/'
    )
    await userEvent.click(screen.getByRole('button', { name: /Cadastrar fonte/ }))

    await waitFor(() =>
      expect(api.post).toHaveBeenCalledWith('/fontes/criar/', {
        nome: 'Informes — Extensão',
        tipo: 'html',
        url: 'https://www.ufca.edu.br/informes/extensao/',
        intervalo_coleta: 60,
      })
    )
    expect(await screen.findByText('Informes — Extensão')).toBeInTheDocument()
  })

  it('avisa que o tipo PDF não tem coletor antes de cadastrar', async () => {
    api.get.mockResolvedValue({ fontes: [] })

    renderFontes()
    await screen.findByText(/Nenhuma fonte cadastrada/)

    await userEvent.selectOptions(screen.getByLabelText('Tipo'), 'pdf')

    expect(screen.getByText(/não tem coletor implementado/)).toBeInTheDocument()
  })

  it('mostra o erro de validação vindo do backend', async () => {
    api.get.mockResolvedValue({ fontes: [] })
    api.post.mockRejectedValue(new Error('url: deve ser uma URL http(s)'))

    renderFontes()
    await screen.findByText(/Nenhuma fonte cadastrada/)

    await userEvent.type(screen.getByLabelText('Nome'), 'X')
    await userEvent.type(screen.getByLabelText('URL'), 'https://x.test/')
    await userEvent.click(screen.getByRole('button', { name: /Cadastrar fonte/ }))

    expect(await screen.findByRole('status')).toHaveTextContent('url: deve ser uma URL http(s)')
  })
})

describe('Fontes — edição', () => {
  it('desativa a fonte e explica o efeito na próxima coleta', async () => {
    api.get.mockResolvedValue({ fontes: [fonte(1)] })
    api.patch.mockResolvedValue(fonte(1, { ativo: false }))

    renderFontes()
    await screen.findByText('Fonte 1')

    await userEvent.click(screen.getByRole('button', { name: 'Desativar' }))

    expect(api.patch).toHaveBeenCalledWith('/fontes/1/', { ativo: false })
    expect(await screen.findByRole('status')).toHaveTextContent(/não será mais coletada/)
  })

  it('salva o intervalo ao sair do campo', async () => {
    api.get.mockResolvedValue({ fontes: [fonte(1)] })
    api.patch.mockResolvedValue(fonte(1, { intervalo_coleta: 120 }))

    renderFontes()
    await screen.findByText('Fonte 1')

    const campo = screen.getByLabelText(/Intervalo de coleta de Fonte 1/)
    await userEvent.clear(campo)
    await userEvent.type(campo, '120')
    await userEvent.tab()

    await waitFor(() =>
      expect(api.patch).toHaveBeenCalledWith('/fontes/1/', { intervalo_coleta: 120 })
    )
  })

  it('recusa intervalo inválido sem chamar a API', async () => {
    api.get.mockResolvedValue({ fontes: [fonte(1)] })

    renderFontes()
    await screen.findByText('Fonte 1')

    const campo = screen.getByLabelText(/Intervalo de coleta de Fonte 1/)
    await userEvent.clear(campo)
    await userEvent.type(campo, '0')
    await userEvent.tab()

    expect(await screen.findByRole('status')).toHaveTextContent(/maior que zero/)
    expect(api.patch).not.toHaveBeenCalled()
  })

  it('explica que fonte com conteúdo não pode ser removida', async () => {
    api.get.mockResolvedValue({ fontes: [fonte(1)] })
    api.delete.mockRejectedValue(
      new Error('Fonte possui conteúdos vinculados; desative em vez de remover.')
    )

    renderFontes()
    await screen.findByText('Fonte 1')

    await userEvent.click(screen.getByRole('button', { name: 'Remover' }))

    expect(await screen.findByRole('status')).toHaveTextContent(/desative em vez de remover/)
    expect(screen.getByText('Fonte 1')).toBeInTheDocument()
  })
})
