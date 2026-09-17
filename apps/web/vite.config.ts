import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  // Served from the root of its own origin in production.
  base: '/',
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8010',
        rewrite: (p) => p.replace(/^\/api/, ''),
        ws: true,
      },
    },
  },
})
