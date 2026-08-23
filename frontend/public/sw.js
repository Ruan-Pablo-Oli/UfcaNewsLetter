// Service worker de notificações push (issue #22, US-04.3).
//
// Fica em `public/` porque o Vite serve esse diretório na raiz — o escopo
// padrão de um service worker é o diretório onde o arquivo é servido, e o
// registro precisa cobrir o site inteiro.

self.addEventListener('push', (event) => {
  if (!event.data) return

  const { title, categoria, url } = event.data.json()
  const body = categoria ? `${categoria}` : ''

  event.waitUntil(
    self.registration.showNotification(title, {
      body,
      data: { url },
    })
  )
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  const url = event.notification.data?.url
  if (!url) return

  event.waitUntil(
    (async () => {
      const clientsList = await self.clients.matchAll({
        type: 'window',
        includeUncontrolled: true,
      })
      const existing = clientsList.find((client) => client.url === url)
      if (existing) {
        await existing.focus()
        return
      }
      await self.clients.openWindow(url)
    })()
  )
})
