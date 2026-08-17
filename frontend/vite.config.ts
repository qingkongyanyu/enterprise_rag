import { fileURLToPath, URL } from 'node:url'

import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

// 开发模式：Vite 5173 端口，/api 与 /health 代理到 FastAPI 8001
// 生产模式：构建产物 dist/ 由 FastAPI 直接托管
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  build: {
    outDir: 'dist',
    chunkSizeWarningLimit: 1200,
    target: 'es2020',
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': { target: 'http://127.0.0.1:8001', changeOrigin: true },
      '/health': { target: 'http://127.0.0.1:8001', changeOrigin: true },
    },
  },
})
