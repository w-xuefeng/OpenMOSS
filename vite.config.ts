import { fileURLToPath, URL } from 'node:url';
import { mkdirSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import vueDevTools from 'vite-plugin-vue-devtools';
import tailwindcss from '@tailwindcss/vite';
import { version } from './package.json';

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    vueDevTools(),
    tailwindcss(),
    // 构建后生成 webui-manifest.json（用于后端版本检查）
    {
      name: 'webui-manifest',
      writeBundle() {
        const outDir = resolve(__dirname, 'dist');
        mkdirSync(outDir, { recursive: true });
        const manifest = {
          version,
          buildTime: new Date().toISOString(),
        };
        writeFileSync(
          resolve(outDir, 'webui-manifest.json'),
          JSON.stringify(manifest, null, 2),
        );
        console.log(`\n  📦 webui-manifest.json generated (v${version})\n`);
      },
    },
  ],
  define: {
    __VERSION__: JSON.stringify(version),
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    host: true,
    proxy: {
      '/api': {
        target: 'http://localhost:6565',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
});
