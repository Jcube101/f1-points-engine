import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  // In production, the React app is served by FastAPI from the same origin,
  // so all /api and /ws requests go to the same host — no proxy needed.
  // In development the Vite dev server (port 5173) proxies those paths to the
  // backend (port 8000) so you don't need to run them on the same port.
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      },
    },
  },
  build: {
    // Emit build artifacts to frontend/dist/ — FastAPI's StaticFiles mount
    // expects this exact path relative to the repo root.
    outDir: 'dist',
    emptyOutDir: true,
  },
})
