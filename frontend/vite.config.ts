import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ command }) => ({
  plugins: [react()],
  base: command === 'build' ? '/static/dist/' : '/',
  build: {
    outDir: '../src/static/dist',
    emptyOutDir: true,
  },
  server: {
    proxy: {
      '/api': 'http://localhost:5001',
      '/feed.xml': 'http://localhost:5001',
      '/health': 'http://localhost:5001',
    },
  },
}));
