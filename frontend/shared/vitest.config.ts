import { defineConfig } from 'vitest/config';

// Pure/api modules run in node; hooks/ui need a DOM → jsdom.
// Per-file environment is selected via a `// @vitest-environment jsdom` docblock
// in the hook/ui test files; the project default stays node for speed.
export default defineConfig({
  test: {
    globals: true,
    environment: 'node',
    setupFiles: ['./vitest.setup.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html'],
      // Global gate is intentionally off (tech-stack Q9=A); pricing is held to 100%.
      include: ['src/**/*.ts', 'src/**/*.tsx'],
      exclude: ['src/types/generated/**', 'src/**/*.test.*', 'src/**/index.ts'],
      thresholds: {
        'src/pricing/**': {
          statements: 100,
          branches: 100,
          functions: 100,
          lines: 100,
        },
      },
    },
  },
});
