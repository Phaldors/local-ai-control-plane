import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// In development the API runs on :8765; the proxy keeps the browser on one origin.
export default defineConfig({
  plugins: [react()],
  server: { proxy: { '/api': 'http://127.0.0.1:8765' } },
  test: { environment: 'jsdom', globals: true, setupFiles: './src/test-setup.ts' },
})
