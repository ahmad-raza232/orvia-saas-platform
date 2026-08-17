import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

function rejectLocalhostTenantApiInProduction() {
  return {
    name: 'reject-localhost-tenant-api',
    configResolved(config) {
      if (!config.isProduction) return
      const url = process.env.VITE_TENANT_API_URL || ''
      if (/localhost|127\.0\.0\.1/i.test(url)) {
        throw new Error(
          'VITE_TENANT_API_URL must not use localhost in a production build. Set it to the public Render API, for example https://<service>.onrender.com/api/v1'
        )
      }
    },
  }
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), rejectLocalhostTenantApiInProduction()],
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  preview: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
