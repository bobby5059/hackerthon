import { defineConfig } from 'tsup';

// ESM-only library build. One entry per public subpath (see package.json "exports").
// React is a peerDependency and must never be bundled.
export default defineConfig({
  entry: {
    'types/index': 'src/types/index.ts',
    'pricing/index': 'src/pricing/index.ts',
    'api/index': 'src/api/index.ts',
    'hooks/index': 'src/hooks/index.ts',
    'ui/index': 'src/ui/index.ts',
  },
  format: ['esm'],
  dts: true,
  sourcemap: true,
  clean: true,
  treeshake: true,
  splitting: false,
  target: 'es2021',
  external: ['react', 'react-dom'],
});
