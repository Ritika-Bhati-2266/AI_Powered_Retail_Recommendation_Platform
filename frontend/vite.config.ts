import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  build: {
    // recharts vendors d3 and is inherently large; with manualChunks it ships in
    // its own opaque 'charts' chunk and only loads when charts render, so the
    // app entry stays small. Raise the warning floor accordingly.
    chunkSizeWarningLimit: 600,
    rollupOptions: {
      output: {
        manualChunks: {
          charts: ['recharts'],
          'ui-icons': ['lucide-react'],
        },
      },
    },
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        // When the backend is down/restarting, return a machine-readable
        // 503 (backend_unreachable) instead of a confusing generic 500 so the
        // UI can tell users "server is starting up" vs a real credentials issue.
        configure: (proxy) => {
          proxy.on('error', (err, _req, res) => {
            const upstream = (err as any)?.address ?? 'backend';
            res.writeHead(503, { 'Content-Type': 'application/json' });
            res.end(
              JSON.stringify({
                error: 'backend_unreachable',
                detail: `The backend (${upstream}) is not reachable — it may be starting up or is currently down.`,
              })
            );
          });
        },
      },
    },
  },
})