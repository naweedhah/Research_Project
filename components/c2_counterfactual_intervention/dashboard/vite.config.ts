import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: '127.0.0.1',
    port: 5173,
    proxy: {
      '/interventions': process.env.C2_API_TARGET ?? 'http://127.0.0.1:8000',
      '/health': process.env.C2_API_TARGET ?? 'http://127.0.0.1:8000',
    },
  },
  test: {
    testTimeout: 15000,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    css: true,
    pool: 'threads',
    maxWorkers: 1,
  },
})
