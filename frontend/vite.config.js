import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  // Em produção a SPA é servida pelo Django/WhiteNoise sob /static/;
  // o index.html vira template e referencia os assets por esse prefixo.
  base: '/static/',
  server: {
    proxy: {
      '/accounts': 'http://localhost:8000',
      '/feed': 'http://localhost:8000',
      '/feedback': 'http://localhost:8000',
      '/busca': 'http://localhost:8000',
      '/historico': 'http://localhost:8000',
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
