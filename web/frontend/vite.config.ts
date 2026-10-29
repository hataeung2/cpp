// Vite config for the playground frontend (spec 070-02).
// Production: `npm run build` → dist/, served by web/server/server.py.
// Development: `npm run dev` (tools/playground.py --dev) proxies /api to the server on
// ATUGCC_API_PORT; the server allows this page's origin through --allow-origin. The page port
// is 5173 unless the CLI gives one (playground.py passes `-- --port N`, spec 070-02-01).
import { defineConfig } from 'vitest/config';

const apiPort = process.env.ATUGCC_API_PORT ?? '8765';

export default defineConfig({
  server: {
    host: '127.0.0.1',
    port: 5173,
    strictPort: true,
    proxy: { '/api': { target: `http://127.0.0.1:${apiPort}`, changeOrigin: true } },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    chunkSizeWarningLimit: 8000, // Monaco and Mermaid are large; this is a local tool
  },
  test: {
    environment: 'jsdom',
    include: ['test/**/*.test.ts'],
  },
});
