import { fileURLToPath, URL } from 'node:url';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const dsRoot = fileURLToPath(new URL('../design-system', import.meta.url));

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { '@ds': `${dsRoot}/src` },
  },
  server: {
    port: 5174,
    open: true,
    fs: { allow: ['.', dsRoot] },
  },
});
