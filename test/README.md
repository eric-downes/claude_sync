# Claude Sync Test Framework

This directory contains the test framework for the Claude Sync project, following a test-driven development (TDD) approach.

## Current Status and Known Issues

The test framework is currently in the process of being set up. There are some configuration issues that need to be resolved:

1. **ESM vs CommonJS**: The project uses ESM modules (`"type": "module"` in package.json), but Jest has some compatibility issues with ESM. We're working on a solution.

2. **TypeScript Integration**: TypeScript tests need special configuration to work with Jest in an ESM environment.

3. **Global Mock Setup**: The setup file for global mocks and utilities needs to be properly integrated with Jest.

### Next Steps for Test Framework Setup

1. Configure Jest to properly handle ESM modules
2. Fix TypeScript integration with Jest
3. Set up proper global mocks and utilities
4. Create working examples of unit tests
5. Add integration test support

Until these issues are resolved, use the test placeholders as specifications for the modules to be implemented.

## Directory Structure

```
test/
├── unit/                      # Unit tests
│   ├── cli/                   # CLI-related tests
│   ├── api/                   # API/browser automation tests
│   ├── sync/                  # Sync engine tests
│   └── mcp/                   # MCP server tests
├── integration/               # Integration tests
├── mocks/                     # Mock implementations
│   ├── claude-web-mock/       # Mock Claude web interface
│   └── fs-mock/               # Mock filesystem
└── utils/                     # Test utilities
```

## Running Tests

To run all tests:

```bash
npm test
```

To run a specific test file:

```bash
npm test -- test/unit/cli/cli.test.ts
```

To run tests with coverage:

```bash
npm test -- --coverage
```

## Mock Services

The test framework includes several mock services to facilitate testing:

### Mock Filesystem

A mock implementation of the filesystem that tracks file changes and emits events, similar to the real filesystem. This allows testing file synchronization without touching the real filesystem.

```typescript
import { createTestFileSystem } from './utils/test-utils';

const mockFs = createTestFileSystem();
mockFs.writeFile('/project/README.md', '# Test Project');
```

### Mock Claude Web Interface

A mock implementation of the Claude.ai web interface that provides HTML responses similar to the real website. This allows testing browser automation without requiring an actual browser or network connection.

```typescript
import { createTestClaudeWeb } from './utils/test-utils';

const mockClaudeWeb = createTestClaudeWeb();
await mockClaudeWeb.login('test@example.com', 'password');
```

## Test Utilities

The `utils/test-utils.ts` file provides various utility functions for testing, including:

- `createTestFileSystem()`: Creates a mock filesystem with sample files
- `createTestClaudeWeb()`: Creates a mock Claude web interface
- `createTempDirName()`: Generates a temporary directory name
- `wait(ms)`: Waits for a specified amount of time
- `createSampleProject()`: Creates a sample project with files
- `compareObjectsIgnoring(obj1, obj2, ignoredFields)`: Compares objects ignoring specific fields

## Writing Tests

Tests follow the Jest testing framework conventions. Each test file should:

1. Import the necessary modules and mocks
2. Set up mocks before importing the module under test
3. Define a test suite with `describe`
4. Use `beforeEach` and `afterEach` for setup and teardown
5. Define individual tests with `test` or `it`
6. Use assertions to verify expected behavior

Example:

```typescript
import { describe, test, expect, jest, beforeEach, afterEach } from '@jest/globals';
import { createTestFileSystem } from '../../utils/test-utils';

// Mock dependencies
jest.mock('fs');

describe('MyModule', () => {
  let mockFs;
  
  beforeEach(() => {
    mockFs = createTestFileSystem();
  });
  
  afterEach(() => {
    jest.clearAllMocks();
  });
  
  test('should do something', () => {
    // Arrange
    const input = 'test';
    
    // Act
    const result = doSomething(input);
    
    // Assert
    expect(result).toBe('expected');
  });
});
```

## Test Placeholders

Many test files contain placeholder tests that will be implemented as the corresponding modules are developed. These placeholders serve as specifications for the expected behavior of the modules.

As you implement each module, you should uncomment and fill in the placeholder tests to verify that your implementation meets the requirements.

## Code Coverage

The test framework is configured to collect code coverage information. You can view the coverage report in the `coverage` directory after running tests with the `--coverage` flag.

Aim for high test coverage, especially for critical components like the sync engine and browser automation.

## Resources

- [Jest Documentation](https://jestjs.io/docs/getting-started)
- [TypeScript Testing Documentation](https://www.typescriptlang.org/docs/handbook/testing.html)
- [Test-Driven Development Guide](https://www.agilealliance.org/glossary/tdd)