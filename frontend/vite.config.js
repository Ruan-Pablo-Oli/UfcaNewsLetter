import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/accounts': 'http://localhost:8000',
      '/feed': 'http://localhost:8000',
      '/feedback': 'http://localhost:8000',
    },
  },
  test: {
    environment: 'jsdom',
    // `globals: true` habilita o cleanup automático do Testing Library entre os
    // testes; ainda assim os testes importam explicitamente de `vitest`.
    globals: true,
    setupFiles: './src/setupTests.js',
  },
})
