import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { isPushSupported, subscribePush, unsubscribePush } from './push'
import { api } from './api'

vi.mock('./api', () => ({
  api: { get: vi.fn(), post: vi.fn(), delete: vi.fn() },
}))

describe('isPushSupported', () => {
  afterEach(() => {
    delete window.PushManager
    delete navigator.serviceWorker
  })

  it('é falso quando o navegador não expõe serviceWorker/PushManager', () => {
    expect(isPushSupported()).toBe(false)
  })

  it('é verdadeiro quando serviceWorker e PushManager existem', () => {
    window.PushManager = function PushManager() {}
    Object.defineProperty(navigator, 'serviceWorker', {
      value: {},
      configurable: true,
      writable: true,
    })

    expect(isPushSupported()).toBe(true)
  })
})

describe('subscribePush', () => {
  let subscription
  let registration

  beforeEach(() => {
    vi.clearAllMocks()
    subscription = {
      toJSON: () => ({
        endpoint: 'https://push.example.com/abc',
        keys: { p256dh: 'chave-p256dh', auth: 'chave-auth' },
      }),
    }
    registration = {
      pushManager: { subscribe: vi.fn().mockResolvedValue(subscription) },
    }
    Object.defineProperty(navigator, 'serviceWorker', {
      value: { register: vi.fn().mockResolvedValue(registration) },
      configurable: true,
      writable: true,
    })
    window.Notification = { requestPermission: vi.fn() }
  })

  afterEach(() => {
    delete navigator.serviceWorker
    delete window.Notification
  })

  it('assina o push e envia a subscription ao backend quando a permissão é concedida', async () => {
    window.Notification.requestPermission.mockResolvedValue('granted')
    api.get.mockResolvedValue({ public_key: 'chave-publica' })
    api.post.mockResolvedValue({})

    const result = await subscribePush()

    expect(result).toEqual({ granted: true })
    expect(navigator.serviceWorker.register).toHaveBeenCalledWith('/sw.js')
    expect(registration.pushManager.subscribe).toHaveBeenCalledWith(
      expect.objectContaining({ userVisibleOnly: true })
    )
    expect(api.post).toHaveBeenCalledWith('/accounts/api/push-subscription/', {
      endpoint: 'https://push.example.com/abc',
      keys: { p256dh: 'chave-p256dh', auth: 'chave-auth' },
    })
  })

  it('não chama o backend quando a permissão é negada', async () => {
    window.Notification.requestPermission.mockResolvedValue('denied')

    const result = await subscribePush()

    expect(result).toEqual({ granted: false })
    expect(registration.pushManager.subscribe).not.toHaveBeenCalled()
    expect(api.get).not.toHaveBeenCalled()
    expect(api.post).not.toHaveBeenCalled()
  })

  it('não chama o backend quando o usuário fecha o prompt sem escolher', async () => {
    window.Notification.requestPermission.mockResolvedValue('default')

    const result = await subscribePush()

    expect(result).toEqual({ granted: false })
    expect(api.post).not.toHaveBeenCalled()
  })
})

describe('unsubscribePush', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    delete window.PushManager
    delete navigator.serviceWorker
  })

  it('não faz nada quando o navegador não suporta push', async () => {
    await unsubscribePush()

    expect(api.delete).not.toHaveBeenCalled()
  })

  it('cancela a subscription e avisa o backend quando existe uma subscription ativa', async () => {
    window.PushManager = function PushManager() {}
    const subscription = {
      toJSON: () => ({ endpoint: 'https://push.example.com/abc' }),
      unsubscribe: vi.fn().mockResolvedValue(true),
    }
    const registration = {
      pushManager: { getSubscription: vi.fn().mockResolvedValue(subscription) },
    }
    Object.defineProperty(navigator, 'serviceWorker', {
      value: { getRegistration: vi.fn().mockResolvedValue(registration) },
      configurable: true,
      writable: true,
    })
    api.delete.mockResolvedValue({})

    await unsubscribePush()

    expect(subscription.unsubscribe).toHaveBeenCalled()
    expect(api.delete).toHaveBeenCalledWith('/accounts/api/push-subscription/', {
      endpoint: 'https://push.example.com/abc',
    })
  })

  it('não chama o backend quando não há registration nem subscription', async () => {
    window.PushManager = function PushManager() {}
    Object.defineProperty(navigator, 'serviceWorker', {
      value: { getRegistration: vi.fn().mockResolvedValue(undefined) },
      configurable: true,
      writable: true,
    })

    await unsubscribePush()

    expect(api.delete).not.toHaveBeenCalled()
  })
})
