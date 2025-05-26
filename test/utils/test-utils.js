/**
 * Utility functions for testing
 */
import { vi } from 'vitest';
import path from 'path';
import crypto from 'crypto';

/**
 * Create a test file system with sample files
 */
export function createTestFileSystem() {
  // This is a mock implementation that simulates a file system
  const files = new Map();
  const directories = new Map();
  
  // Helper to create a mock file system object
  const createMockFs = () => {
    return {
      // File operations
      readFileSync: vi.fn((filePath) => {
        if (!files.has(filePath)) {
          throw new Error(`File not found: ${filePath}`);
        }
        return files.get(filePath);
      }),
      
      writeFileSync: vi.fn((filePath, content) => {
        files.set(filePath, content);
        // Update the parent directory
        const dirPath = path.dirname(filePath);
        if (!directories.has(dirPath)) {
          directories.set(dirPath, []);
        }
        const dirContents = directories.get(dirPath);
        if (!dirContents.includes(path.basename(filePath))) {
          dirContents.push(path.basename(filePath));
        }
      }),
      
      unlinkSync: vi.fn((filePath) => {
        if (!files.has(filePath)) {
          throw new Error(`File not found: ${filePath}`);
        }
        files.delete(filePath);
        // Update the parent directory
        const dirPath = path.dirname(filePath);
        if (directories.has(dirPath)) {
          const dirContents = directories.get(dirPath);
          const fileIndex = dirContents.indexOf(path.basename(filePath));
          if (fileIndex !== -1) {
            dirContents.splice(fileIndex, 1);
          }
        }
      }),
      
      // Directory operations
      mkdirSync: vi.fn((dirPath, options) => {
        directories.set(dirPath, []);
        // Update the parent directory
        const parentDir = path.dirname(dirPath);
        if (parentDir !== dirPath && !directories.has(parentDir)) {
          if (options?.recursive) {
            // Create parent directories if recursive
            directories.set(parentDir, []);
          } else {
            throw new Error(`Parent directory not found: ${parentDir}`);
          }
        }
        // Add to parent directory
        if (parentDir !== dirPath) {
          const parentContents = directories.get(parentDir) || [];
          if (!parentContents.includes(path.basename(dirPath))) {
            parentContents.push(path.basename(dirPath));
            directories.set(parentDir, parentContents);
          }
        }
      }),
      
      readdirSync: vi.fn((dirPath) => {
        if (!directories.has(dirPath)) {
          throw new Error(`Directory not found: ${dirPath}`);
        }
        return directories.get(dirPath);
      }),
      
      // Status operations
      statSync: vi.fn((filePath) => {
        const isFile = files.has(filePath);
        const isDirectory = directories.has(filePath);
        
        if (!isFile && !isDirectory) {
          throw new Error(`No such file or directory: ${filePath}`);
        }
        
        return {
          isFile: () => isFile,
          isDirectory: () => isDirectory,
          mtime: new Date(),
          size: isFile ? files.get(filePath).length : 0
        };
      }),
      
      existsSync: vi.fn((filePath) => {
        return files.has(filePath) || directories.has(filePath);
      }),
      
      // Watchers
      watch: vi.fn((path, options, listener) => {
        // Simple mock that doesn't actually watch
        return {
          close: vi.fn()
        };
      })
    };
  };
  
  const mockFs = createMockFs();
  
  // Create some initial directories and files
  mockFs.mkdirSync('/project', { recursive: true });
  mockFs.mkdirSync('/project/src', { recursive: true });
  mockFs.mkdirSync('/project/docs', { recursive: true });
  mockFs.mkdirSync('/project/tests', { recursive: true });
  
  mockFs.writeFileSync('/project/README.md', '# Test Project\n\nThis is a test project for Claude Sync.');
  mockFs.writeFileSync('/project/src/main.js', 'console.log("Hello, Claude!");');
  mockFs.writeFileSync('/project/src/utils.js', 'export function add(a, b) { return a + b; }');
  mockFs.writeFileSync('/project/docs/api.md', '# API Documentation\n\nThis document describes the API.');
  mockFs.writeFileSync('/project/tests/main.test.js', 'test("should work", () => { expect(true).toBe(true); });');
  
  return mockFs;
}

/**
 * Create a temporary directory name
 */
export function createTempDirName() {
  return path.join('/tmp', `claude-sync-test-${crypto.randomBytes(8).toString('hex')}`);
}

/**
 * Create a sample project for testing
 */
export function createSampleProject(id = null, name = 'Sample Project') {
  const projectId = id || `proj_${crypto.randomBytes(8).toString('hex')}`;
  
  return {
    id: projectId,
    name,
    description: `A sample project for testing`,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    ownerId: 'user_123',
    isShared: false,
    knowledgeBase: {
      id: `kb_${projectId}`,
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
 * Wait for a specified amount of time
 */
export function wait(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Compare two objects ignoring specific fields
 */
export function compareObjectsIgnoring(obj1, obj2, ignoredFields = []) {
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