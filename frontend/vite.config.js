import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// During development, requests to /api can be proxied to your Python backend.
// Change the target to wherever your RAG API runs (e.g. FastAPI/Flask on 8000).
export default defineConfig({
  plugins: [react()],
  server: { proxy: { '/api': { target: 'http://localhost:8000', changeOrigin: true } } }
})
