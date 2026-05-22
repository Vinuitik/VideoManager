import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    // In dev mode, proxy /api calls to FastAPI so you don't need nginx running locally
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        ws: true,  // also proxy WebSocket connections
      },
    },
  },
})
