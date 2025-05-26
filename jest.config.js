/** @type {import('ts-jest').JestConfigWithTsJest} */
export default {
  preset: 'ts-jest',
  testEnvironment: 'node',
  transform: {
    '^.+\\.tsx?$': ['ts-jest', {
      isolatedModules: true,
    }]
  },
  // Add coverage collection
  collectCoverage: true,
  collectCoverageFrom: [
    'src/**/*.ts',
    '!src/**/*.d.ts',
    '!src/**/*.test.ts',
  ],
  coverageDirectory: 'coverage',
  coverageReporters: ['text', 'lcov'],
  // Use different test patterns
  testMatch: [
    '**/test/**/*.test.ts',
    '**/test/**/*.test.js',
    '**/src/**/*.test.ts'
  ],
  // Setup test utilities
  setupFilesAfterEnv: ['./test/setup.js'],
  // Test timeouts
  testTimeout: 10000,
  // Test reporting
  reporters: ['default'],
  // Test environment variables
  testEnvironmentOptions: {
    url: 'http://localhost/'
  },
};