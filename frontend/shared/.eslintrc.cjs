/* eslint-env node */
module.exports = {
  root: true,
  parser: '@typescript-eslint/parser',
  parserOptions: {
    ecmaVersion: 2021,
    sourceType: 'module',
    ecmaFeatures: { jsx: true },
  },
  plugins: ['@typescript-eslint'],
  extends: ['eslint:recommended', 'plugin:@typescript-eslint/recommended', 'prettier'],
  env: {
    browser: true,
    es2021: true,
  },
  ignorePatterns: ['dist', 'node_modules', 'src/types/generated'],
  rules: {
    // Security Baseline SECURITY-03: the library must not log. Surface console use as an error.
    'no-console': 'error',
    '@typescript-eslint/no-unused-vars': [
      'error',
      { argsIgnorePattern: '^_', varsIgnorePattern: '^_' },
    ],
    '@typescript-eslint/consistent-type-imports': 'error',
  },
  overrides: [
    {
      files: ['**/*.test.ts', '**/*.test.tsx'],
      env: { node: true },
      rules: { 'no-console': 'off' },
    },
  ],
};
