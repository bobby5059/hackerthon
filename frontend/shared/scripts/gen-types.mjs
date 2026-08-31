#!/usr/bin/env node
/**
 * OpenAPI → TypeScript codegen wrapper (tech-stack Q8=A, NFR-design MP-01).
 *
 * Regenerates `src/types/generated/schema.ts` from the committed backend
 * contract snapshot `openapi.json`. The generated file is a build artifact —
 * never edit it by hand; update `openapi.json` (per Integration Contract §9)
 * and re-run this script.
 *
 * CI drift gate: run this, then `git diff --exit-code src/types/generated`.
 * A non-empty diff means the snapshot and committed types are out of sync.
 */
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';
import { spawnSync } from 'node:child_process';

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, '..');
const input = resolve(root, 'openapi.json');
const output = resolve(root, 'src/types/generated/schema.ts');

const result = spawnSync(
  'npx',
  ['openapi-typescript', input, '-o', output, '--root-types'],
  { stdio: 'inherit', cwd: root },
);

if (result.status !== 0) {
  process.exit(result.status ?? 1);
}
