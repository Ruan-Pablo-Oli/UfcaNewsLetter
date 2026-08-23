import { api } from './api'

const SERVICE_WORKER_URL = '/sw.js'
const SUBSCRIPTION_ENDPOINT = '/accounts/api/push-subscription/'
const VAPID_PUBLIC_KEY_ENDPOINT = '/accounts/api/vapid-public-key/'

export function isPushSupported() {
  return 'serviceWorker' in navigator && 'PushManager' in window
}

function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4)
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
  const rawData = atob(base64)
  return Uint8Array.from([...rawData].map((char) => char.charCodeAt(0)))
}

// Registra o service worker, pede permissão de notificação e assina o
// PushManager, enviando a subscription ao backend. Não chama o backend se a
// permissão não for concedida (negada, ou prompt fechado sem escolha).
export async function subscribePush() {
  const registration = await navigator.serviceWorker.register(SERVICE_WORKER_URL)

  const permission = await Notification.requestPermission()
  if (permission !== 'granted') {
    return { granted: false }
  }

  const { public_key: publicKey } = await api.get(VAPID_PUBLIC_KEY_ENDPOINT)
  const subscription = await registration.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(publicKey),
  })

  const { endpoint, keys } = subscription.toJSON()
  await api.post(SUBSCRIPTION_ENDPOINT, { endpoint, keys })
  return { granted: true }
}

// Cancela a subscription no navegador e avisa o backend para removê-la.
export async function unsubscribePush() {
  if (!isPushSupported()) return

  const registration = await navigator.serviceWorker.getRegistration()
  const subscription = await registration?.pushManager.getSubscription()
  if (!subscription) return

  const { endpoint } = subscription.toJSON()
  await subscription.unsubscribe()
  await api.delete(SUBSCRIPTION_ENDPOINT, { endpoint })
}
