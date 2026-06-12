import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// HM44.2: Real Vite production build.
// Input: app.html (passphrase-gated React SPA)
// Output: dist/ (served by FastAPI StaticFiles)
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    rollupOptions: {
      input: 'app.html',
    },
  },
})
