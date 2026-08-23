import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'

import { Perfil } from './Perfil'
import { api } from '../api'

vi.mock('../api', () => ({
  api: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}))

vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({
    user: { username: 'aluno', email: 'aluno@ufca.edu.br' },
    logout: vi.fn(),
  }),
}))

// base64url válido (65 bytes): `atob`, em urlBase64ToUint8Array,
// rejeita qualquer coisa fora do alfabeto base64.
const VAPID_PUBLIC_KEY = 'BEl62iUYgUivxIkv69yViEuiBIa-Ib9-SkvMeAtA3LFgDzkrxZJjSgSnfckjBJuBkr3qBUYIHBQFLXYp5Nksh8U'

function mockPerfilApi({ pushAtivo = false } = {}) {
  api.get.mockImplementation((url) => {
    switch (url) {
      case '/accounts/api/perfil/':
        return Promise.resolve({
          curso: 'engenharia_de_software',
          periodo: 3,
          interesses: [],
          frequencia_email: 'diaria',
          push_ativo: pushAtivo,
        })
      case '/accounts/api/cursos/':
        return Promise.resolve({
          cursos: [{ value: 'engenharia_de_software', label: 'Engenharia de Software' }],
        })
      case '/accounts/api/interesses/':
        return Promise.resolve({ interesses: [] })
      case '/accounts/api/frequencias-email/':
        return Promise.resolve({ frequencias: [{ value: 'diaria', label: 'Diária' }] })
      case '/accounts/api/vapid-public-key/':
        return Promise.resolve({ public_key: VAPID_PUBLIC_KEY })
      default:
        return Promise.reject(new Error(`GET inesperado: ${url}`))
    }
  })
}

function renderPerfil() {
  return render(
    <MemoryRouter>
      <Perfil />
    </MemoryRouter>
  )
}

async function abrirAbaEntrega() {
  // findBy*, não getBy*: a tela fica em loading até o load() assíncrono
  // resolver, e só então as abas são renderizadas.
  await userEvent.click(await screen.findByRole('button', { name: 'Frequência de entrega' }))
}

describe('Perfil — notificações push', () => {
  let subscription
  let registration

  beforeEach(() => {
    vi.clearAllMocks()

    subscription = {
      endpoint: 'https://push.example.com/abc',
      toJSON: () => ({
        endpoint: 'https://push.example.com/abc',
        keys: { p256dh: 'chave-p256dh', auth: 'chave-auth' },
      }),
      unsubscribe: vi.fn().mockResolvedValue(true),
    }
    registration = {
      pushManager: {
        subscribe: vi.fn().mockResolvedValue(subscription),
        getSubscription: vi.fn().mockResolvedValue(subscription),
      },
    }

    window.PushManager = function PushManager() {}
    Object.defineProperty(navigator, 'serviceWorker', {
      value: {
        register: vi.fn().mockResolvedValue(registration),
        getRegistration: vi.fn().mockResolvedValue(registration),
      },
      configurable: true,
      writable: true,
    })
    window.Notification = {
      permission: 'default',
      requestPermission: vi.fn().mockResolvedValue('granted'),
    }
  })

  afterEach(() => {
    delete window.PushManager
    delete navigator.serviceWorker
    delete window.Notification
  })

  it('liga o toggle: registra o service worker, assina o push e envia a subscription ao backend', async () => {
    mockPerfilApi({ pushAtivo: false })
    api.patch.mockResolvedValue({})
    api.post.mockResolvedValue({})
    renderPerfil()
    await abrirAbaEntrega()

    const toggle = await screen.findByRole('switch', { name: 'Notificações push' })
    expect(toggle).not.toBeChecked()

    await userEvent.click(toggle)

    expect(navigator.serviceWorker.register).toHaveBeenCalledWith('/sw.js')
    expect(window.Notification.requestPermission).toHaveBeenCalled()
    expect(registration.pushManager.subscribe).toHaveBeenCalled()
    expect(api.post).toHaveBeenCalledWith('/accounts/api/push-subscription/', {
      endpoint: 'https://push.example.com/abc',
      keys: { p256dh: 'chave-p256dh', auth: 'chave-auth' },
    })
    expect(api.patch).toHaveBeenCalledWith(
      '/accounts/api/perfil/',
      expect.objectContaining({ push_ativo: true })
    )
    expect(await screen.findByRole('switch', { name: 'Notificações push' })).toBeChecked()
  })

  it('desliga o toggle: cancela a subscription no navegador e avisa o backend', async () => {
    mockPerfilApi({ pushAtivo: true })
    api.patch.mockResolvedValue({})
    api.delete.mockResolvedValue({})
    renderPerfil()
    await abrirAbaEntrega()

    const toggle = await screen.findByRole('switch', { name: 'Notificações push' })
    expect(toggle).toBeChecked()

    await userEvent.click(toggle)

    expect(navigator.serviceWorker.getRegistration).toHaveBeenCalledWith()
    expect(subscription.unsubscribe).toHaveBeenCalled()
    expect(api.delete).toHaveBeenCalledWith('/accounts/api/push-subscription/', {
      endpoint: 'https://push.example.com/abc',
    })
    expect(api.patch).toHaveBeenCalledWith(
      '/accounts/api/perfil/',
      expect.objectContaining({ push_ativo: false })
    )
    expect(await screen.findByRole('switch', { name: 'Notificações push' })).not.toBeChecked()
  })

  it('permissão negada: mostra orientação, desabilita o toggle e não chama o backend', async () => {
    mockPerfilApi({ pushAtivo: false })
    window.Notification.permission = 'denied'
    renderPerfil()
    await abrirAbaEntrega()

    const toggle = await screen.findByRole('switch', { name: 'Notificações push' })
    expect(toggle).toBeDisabled()
    expect(
      screen.getByText(/notificações estão bloqueadas nas configurações do navegador/i)
    ).toBeInTheDocument()

    expect(navigator.serviceWorker.register).not.toHaveBeenCalled()
    expect(api.post).not.toHaveBeenCalled()
    expect(api.patch).not.toHaveBeenCalled()
  })

  it('navegador sem suporte: não renderiza o toggle', async () => {
    delete window.PushManager
    mockPerfilApi({ pushAtivo: false })
    renderPerfil()
    await abrirAbaEntrega()

    expect(screen.queryByRole('switch', { name: 'Notificações push' })).not.toBeInTheDocument()
    expect(
      screen.getByText(/notificações push não são suportadas neste navegador/i)
    ).toBeInTheDocument()
  })
})
