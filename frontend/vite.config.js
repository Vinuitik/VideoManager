import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],

  // Test config lives here — vitest reads it from vite.config.js automatically
  test: {
    environment: 'jsdom',       // simulates a browser DOM for React components
    globals: true,              // gives you describe/it/expect without importing them
    setupFiles: './src/test-setup.js',
  },

  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        ws: true,
      },
    },
  },
})
