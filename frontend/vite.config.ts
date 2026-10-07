import path from 'node:path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// The backend (`uv run fastapi dev` in backend/) listens on 127.0.0.1:8000.
// The browser talks only to Vite; Vite forwards /api to the backend, so no CORS is needed.
const proxy = {
  '/api': 'http://127.0.0.1:8000',
}

// https://vite.dev/config/
export default defineConfig({
  server: { proxy },
  preview: { proxy },
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(import.meta.dirname, './src'),
    },
  },
})
