/**
 * Global test setup for Claude Sync
 */

// Set timeout for all tests to prevent hanging
jest.setTimeout(10000);

// Create global mocks
global.consoleMock = {
  log: jest.fn(),
  error: jest.fn(),
  warn: jest.fn(),
  info: jest.fn(),
};

// Mock environment variables for testing
process.env.NODE_ENV = 'test';
process.env.CLAUDE_API_KEY = 'test-api-key';
process.env.CLAUDE_AUTH_TOKEN = 'test-auth-token';

// Create helper functions for tests
global.createMockProject = (id, name) => {
  return {
    id,
    name,
    description: `Mock project ${name}`,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    ownerId: 'user_123',
    isShared: false,
    knowledgeBase: {
      id: `kb_${id}`,
      fileCount: 0,
      totalSizeBytes: 0,
      lastUpdated: new Date().toISOString()
    }
  };
};

// Handle uncaught errors during tests
process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled Rejection during test execution:', reason);
});