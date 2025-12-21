import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  publicDir: 'public', // ระบุ public directory
  server: {
    port: 5173,
    open: '/', // เปิด root เมื่อ start server
  }
})
