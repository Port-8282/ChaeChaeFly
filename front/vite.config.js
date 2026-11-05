import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), 'BACKEND_')
  const target = env.BACKEND_URL || 'http://127.0.0.1:8080'

  return {
    plugins: [vue()],
    server: {
      host: '127.0.0.1',
      port: 5173,
      strictPort: true,
      proxy: {
        '/api': { target, changeOrigin: true },
        '/actuator': { target, changeOrigin: true },
      },
    },
    preview: {
      proxy: {},
      host: '127.0.0.1',
      port: 4173,
      strictPort: true,
    },
  }
})
