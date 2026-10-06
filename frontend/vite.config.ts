import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    watch: {
      // 啟用輪詢機制，確保在 Docker 卷掛載或 Windows 網路磁碟環境下即時觸發 HMR
      usePolling: true,
    },
    proxy: {
      '/api': {
        // 開發環境優先讀取環境變數 VITE_API_PROXY_TARGET (如 Docker 內部 http://backend:8000)，預設為本機 http://localhost:8000
        target: process.env.VITE_API_PROXY_TARGET || 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
  },
})
