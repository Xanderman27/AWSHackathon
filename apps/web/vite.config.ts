import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  // Served from the root of its own origin in production.
  base: '/',
  plugins: [react()],
  server: {
    // Listen on the network too, so two students on different computers on the same
    // Wi-Fi can both open the app (http://<this-machine's-ip>:5173).
    host: true,
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
