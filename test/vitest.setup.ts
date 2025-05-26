import { vi } from 'vitest';

// Set test environment variables
process.env.NODE_ENV = 'test';
process.env.CLAUDE_API_KEY = 'test-api-key';
process.env.CLAUDE_AUTH_TOKEN = 'test-auth-token';

// Define global types
declare global {
  var consoleMock: {
    log: ReturnType<typeof vi.fn>;
    error: ReturnType<typeof vi.fn>;
    warn: ReturnType<typeof vi.fn>;
    info: ReturnType<typeof vi.fn>;
  };
  
  function createMockProject(id: string, name: string): {
    id: string;
    name: string;
    description: string;
    createdAt: string;
    updatedAt: string;
    ownerId: string;
    isShared: boolean;
    knowledgeBase: {
      id: string;
      fileCount: number;
      totalSizeBytes: number;
      lastUpdated: string;
    };
  };
}

// Create global mocks
global.consoleMock = {
  log: vi.fn(),
  error: vi.fn(),
  warn: vi.fn(),
  info: vi.fn(),
};

// Create helper function to create mock projects
global.createMockProject = (id: string, name: string) => {
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
process.on('unhandledRejection', (reason) => {
  console.error('Unhandled Rejection during test execution:', reason);
});