import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  build: { manifest: true, rollupOptions: { input: { main: 'index.html', publicPapers: 'src/publicPapers.js' } } },
  server: { port: 5173, proxy: { '/api': 'http://localhost:8000' } }
})
