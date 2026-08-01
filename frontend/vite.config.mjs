import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

const readFirst = (env, ...keys) => {
  for (const key of keys) {
    if (env[key] !== undefined) return env[key];
  }
  return '';
};

export default defineConfig(({ mode, isSsrBuild }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const backendUrl = env.BACKEND_API_URL || 'http://localhost:8000';

  return {
    plugins: [react()],
    envPrefix: ['VITE_', 'REACT_APP_'],
    define: {
      'process.env.NODE_ENV': JSON.stringify(mode === 'production' ? 'production' : 'development'),
      'process.env.REACT_APP_API_BASE_URL': JSON.stringify(
        readFirst(env, 'VITE_API_BASE_URL', 'REACT_APP_API_BASE_URL'),
      ),
      'process.env.REACT_APP_PUBLIC_ORIGIN': JSON.stringify(
        readFirst(env, 'VITE_PUBLIC_ORIGIN', 'REACT_APP_PUBLIC_ORIGIN'),
      ),
      'process.env.REACT_APP_VAPID_PUBLIC_KEY': JSON.stringify(
        readFirst(env, 'VITE_VAPID_PUBLIC_KEY', 'REACT_APP_VAPID_PUBLIC_KEY'),
      ),
      'process.env.REACT_APP_ANALYTICS_ENABLED': JSON.stringify(
        readFirst(env, 'VITE_ANALYTICS_ENABLED', 'REACT_APP_ANALYTICS_ENABLED'),
      ),
    },
    server: {
      host: '0.0.0.0',
      port: 3000,
      proxy: {
        '/api': {
          target: backendUrl,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api(?=\/|$)/, '') || '/',
        },
        '/mcp': {
          target: backendUrl,
          changeOrigin: true,
        },
      },
    },
    ssr: {
      noExternal: true,
    },
    build: isSsrBuild
      ? {
          copyPublicDir: false,
          rollupOptions: {
            output: {
              entryFileNames: '[name].mjs',
              chunkFileNames: 'chunks/[name]-[hash].mjs',
            },
          },
        }
      : undefined,
    test: {
      globals: true,
      environment: 'jsdom',
      setupFiles: './src/setupTests.js',
      include: ['src/**/*.test.{js,jsx}'],
      css: true,
      clearMocks: true,
      coverage: {
        provider: 'v8',
        reporter: ['text-summary'],
        include: ['src/**/*.{js,jsx}'],
        exclude: [
          'src/**/*.test.{js,jsx}',
          'src/setupTests.js',
        ],
        thresholds: {
          branches: 14,
          functions: 10,
          lines: 14,
          statements: 14,
        },
      },
    },
  };
});
