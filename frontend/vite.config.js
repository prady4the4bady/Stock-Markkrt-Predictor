import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true,
        drop_debugger: true
      }
    },
    rollupOptions: {
      output: {
        manualChunks: {
          vendor:     ['react', 'react-dom', 'react-router-dom'],
          charts:     ['recharts'],
          animations: ['framer-motion'],
          // react-globe.gl bundles Three.js (~1.8MB) — isolate into its own chunk
          // so it only loads when the Globe view is opened (lazy import)
          globe:      ['react-globe.gl'],
        }
      }
    },
    chunkSizeWarningLimit: 2000
  },
  define: {
    __APP_VERSION__: JSON.stringify(process.env.npm_package_version || '1.0.0')
  }
})
