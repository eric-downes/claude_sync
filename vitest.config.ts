import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    // Enable global test utilities
    globals: true,
    
    // Set environment
    environment: 'node',
    
    // Include files
    include: ['./test/**/*.test.{js,ts}', './src/**/*.test.{js,ts}'],
    
    // Exclude files
    exclude: ['**/node_modules/**', '**/dist/**'],
    
    // Set test timeout
    testTimeout: 10000,
    
    // Setup files to run before tests
    setupFiles: ['./test/vitest.setup.ts'],
    
    // Code coverage
    coverage: {
      provider: 'v8',
      reporter: ['text', 'lcov'],
      include: ['src/**/*.ts'],
      exclude: ['**/*.test.ts', '**/*.d.ts'],
    },
    
    // Watch mode settings
    watchExclude: ['**/node_modules/**', '**/dist/**'],
  }
});