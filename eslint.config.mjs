import js from '@eslint/js';
import tseslint from 'typescript-eslint';

export default [
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      globals: {
        // Browser globals
        window: 'readonly',
        document: 'readonly',
        console: 'readonly',
        fetch: 'readonly',
        AbortSignal: 'readonly',
        Response: 'readonly',
        Request: 'readonly',
        URL: 'readonly',

        // Node globals
        process: 'readonly',
        __dirname: 'readonly',
        __filename: 'readonly',
        module: 'readonly',
        require: 'readonly',
        exports: 'readonly',

        // TypeScript/Cloudflare Workers globals
        KVNamespace: 'readonly',
      },
    },
    rules: {
      'no-console': 'off', // Allow console in Cloudflare Workers
      'no-unused-vars': 'off', // Using TS version instead
      '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
      '@typescript-eslint/no-explicit-any': 'warn', // Warn but don't fail on any
      'no-var': 'error',
      'prefer-const': 'error',
      'eqeqeq': ['error', 'always'],
      'curly': ['error', 'all'],
      'complexity': ['warn', 10],
      'max-depth': ['warn', 4],
      'max-lines-per-function': [
        'warn',
        { max: 100, skipBlankLines: true, skipComments: true },
      ],
      'max-params': ['warn', 4],
      'no-magic-numbers': 'off', // Too noisy for this project
      'no-duplicate-imports': 'error',
      'no-eval': 'error',
      'no-implied-eval': 'error',
      'no-new-func': 'error',
      'no-return-await': 'error',
      'require-await': 'error',
      'no-throw-literal': 'error',
    },
  },
];
