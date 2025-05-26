/**
 * Utility functions for testing
 */
import { MockFileSystem } from '../mocks/fs-mock/mock-filesystem.js';
import { MockClaudeWeb } from '../mocks/claude-web-mock/mock-claude-web.js';
import path from 'path';
import crypto from 'crypto';

/**
 * Create a test file system with sample files
 */
export function createTestFileSystem(): MockFileSystem {
  const fs = new MockFileSystem();
  
  // Create a sample project structure
  fs.mkdirp('/project/src');
  fs.mkdirp('/project/docs');
  fs.mkdirp('/project/tests');
  
  // Add some sample files
  fs.writeFile('/project/README.md', '# Test Project\n\nThis is a test project for Claude Sync.');
  fs.writeFile('/project/src/main.js', 'console.log("Hello, Claude!");');
  fs.writeFile('/project/src/utils.js', 'export function add(a, b) { return a + b; }');
  fs.writeFile('/project/docs/api.md', '# API Documentation\n\nThis document describes the API.');
  fs.writeFile('/project/tests/main.test.js', 'test("should work", () => { expect(true).toBe(true); });');
  
  return fs;
}

/**
 * Create a temporary directory name
 */
export function createTempDirName(): string {
  return path.join('/tmp', `claude-sync-test-${crypto.randomBytes(8).toString('hex')}`);
}

/**
 * Create a test Claude web client
 */
export function createTestClaudeWeb(): MockClaudeWeb {
  return new MockClaudeWeb();
}

/**
 * Wait for a specified amount of time
 */
export async function wait(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Create a sample project with files
 */
export function createSampleProject() {
  return {
    id: `proj_${crypto.randomBytes(8).toString('hex')}`,
    name: 'Sample Project',
    description: 'A sample project for testing',
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    ownerId: 'user_123',
    isShared: false,
    knowledgeBase: {
      id: `kb_${crypto.randomBytes(8).toString('hex')}`,
      fileCount: 3,
      totalSizeBytes: 1024,
      lastUpdated: new Date().toISOString()
    },
    files: [
      {
        id: `file_${crypto.randomBytes(8).toString('hex')}`,
        name: 'README.md',
        content: '# Sample Project\n\nThis is a sample project for testing Claude Sync.',
        path: 'README.md',
        sizeBytes: 100,
        mimeType: 'text/markdown',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString()
      },
      {
        id: `file_${crypto.randomBytes(8).toString('hex')}`,
        name: 'main.js',
        content: 'console.log("Hello, Claude!");',
        path: 'src/main.js',
        sizeBytes: 50,
        mimeType: 'application/javascript',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString()
      },
      {
        id: `file_${crypto.randomBytes(8).toString('hex')}`,
        name: 'api.md',
        content: '# API Documentation\n\nThis document describes the API.',
        path: 'docs/api.md',
        sizeBytes: 74,
        mimeType: 'text/markdown',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString()
      }
    ]
  };
}

/**
 * Compare two objects ignoring specific fields
 */
export function compareObjectsIgnoring(obj1: any, obj2: any, ignoredFields: string[] = []): boolean {
  if (typeof obj1 !== typeof obj2) {
    return false;
  }
  
  if (typeof obj1 !== 'object' || obj1 === null || obj2 === null) {
    return obj1 === obj2;
  }
  
  const keys1 = Object.keys(obj1).filter(key => !ignoredFields.includes(key));
  const keys2 = Object.keys(obj2).filter(key => !ignoredFields.includes(key));
  
  if (keys1.length !== keys2.length) {
    return false;
  }
  
  return keys1.every(key => {
    if (ignoredFields.includes(key)) {
      return true;
    }
    
    if (typeof obj1[key] === 'object' && obj1[key] !== null) {
      return compareObjectsIgnoring(obj1[key], obj2[key], ignoredFields);
    }
    
    return obj1[key] === obj2[key];
  });
}