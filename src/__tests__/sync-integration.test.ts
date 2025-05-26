import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import path from 'path';
import os from 'os';
import fs from 'fs/promises';
import { MockClaudeClient } from '../api/mock-claude-client.js';
import { syncFiles } from '../sync/sync.js';
import * as configure from '../config/configure.js';
import { ClaudeClientFactory } from '../api/client-factory.js';

// Mock the dependencies
vi.mock('../config/configure.js');
vi.mock('../api/client-factory.js');

describe('Sync Integration', () => {
  let tempDir: string;
  let mockClient: MockClaudeClient;
  let projectId: string;
  let projectConfig: any;
  
  // Helper function to recursively get all files
  async function getAllFilesRecursive(dir: string): Promise<string[]> {
    const files: string[] = [];
    async function scan(currentDir: string): Promise<void> {
      try {
        const entries = await fs.readdir(currentDir, { withFileTypes: true });
        for (const entry of entries) {
          const fullPath = path.join(currentDir, entry.name);
          if (entry.isDirectory()) {
            await scan(fullPath);
          } else {
            files.push(path.relative(dir, fullPath));
          }
        }
      } catch (error) {
        // Directory might not exist
      }
    }
    await scan(dir);
    return files;
  }
  
  beforeEach(async () => {
    vi.clearAllMocks();
    
    // Mock console methods to suppress output during tests
    vi.spyOn(console, 'log').mockImplementation(() => {});
    vi.spyOn(console, 'error').mockImplementation(() => {});
    
    // Create a temp directory path
    tempDir = path.join(os.tmpdir(), `claude-sync-test-${Date.now()}`);
    
    // Create a mock client
    mockClient = new MockClaudeClient();
    
    // Mock the client factory to return our mock client
    vi.mocked(ClaudeClientFactory.getClient).mockReturnValue(mockClient);
    
    // Get a project ID from the mock client
    const projects = await mockClient.listProjects();
    projectId = projects[0].id;
    
    // Create project config
    projectConfig = {
      projectId,
      localPath: tempDir,
      excludePatterns: ['node_modules/**', '.git/**', '*.log']
    };
    
    // Mock configuration functions
    vi.mocked(configure.getProjectConfig).mockReturnValue(projectConfig);
    vi.mocked(configure.updateLastSynced).mockImplementation(() => {});
    
    // Create temp directory
    await fs.mkdir(tempDir, { recursive: true });
  });
  
  afterEach(async () => {
    vi.restoreAllMocks();
    
    // Clean up temp directory
    try {
      await fs.rm(tempDir, { recursive: true, force: true });
    } catch (error) {
      // Ignore cleanup errors
    }
  });
  
  it('should upload local files to Claude project', async () => {
    // Create test files in temp directory
    const srcDir = path.join(tempDir, 'src');
    await fs.mkdir(srcDir, { recursive: true });
    
    const testFiles = {
      'src/main.ts': 'console.log("Hello, Claude!");',
      'README.md': '# Test Project\n\nThis is a test project for sync integration.',
      'package.json': JSON.stringify({ name: 'test-project', version: '1.0.0' }, null, 2)
    };
    
    // Write test files
    for (const [filePath, content] of Object.entries(testFiles)) {
      const fullPath = path.join(tempDir, filePath);
      await fs.mkdir(path.dirname(fullPath), { recursive: true });
      await fs.writeFile(fullPath, content);
    }
    
    // Sync files (upload only)
    await syncFiles('test-project', 'upload');
    
    // Verify files were uploaded to the mock client
    const uploadedFiles = await mockClient.listKnowledgeFiles(projectId);
    expect(uploadedFiles).toHaveLength(3);
    
    // Check that the correct files were uploaded
    const filePaths = uploadedFiles.map(f => f.path).sort();
    expect(filePaths).toEqual(['README.md', 'package.json', 'src/main.ts']);
    
    // Verify file contents
    const mainFile = uploadedFiles.find(f => f.path === 'src/main.ts');
    expect(mainFile?.content).toBe('console.log("Hello, Claude!");');
    
    const readmeFile = uploadedFiles.find(f => f.path === 'README.md');
    expect(readmeFile?.content).toBe('# Test Project\n\nThis is a test project for sync integration.');
  });
  
  it('should download files from Claude project to local directory', async () => {
    // First, upload some files to the mock client
    const testFiles = [
      { name: 'src/app.ts', content: 'export class App {}' },
      { name: 'docs/guide.md', content: '# User Guide\n\nHow to use this app.' },
      { name: 'config.json', content: '{"debug": true}' }
    ];
    
    for (const file of testFiles) {
      await mockClient.uploadKnowledgeFile(projectId, file.name, file.content);
    }
    
    // Sync files (download only)
    await syncFiles('test-project', 'download');
    
    // Verify files were downloaded to the temp directory
    const appFile = await fs.readFile(path.join(tempDir, 'src/app.ts'), 'utf-8');
    expect(appFile).toBe('export class App {}');
    
    const guideFile = await fs.readFile(path.join(tempDir, 'docs/guide.md'), 'utf-8');
    expect(guideFile).toBe('# User Guide\n\nHow to use this app.');
    
    const configFile = await fs.readFile(path.join(tempDir, 'config.json'), 'utf-8');
    expect(configFile).toBe('{"debug": true}');
  });
  
  it('should sync bidirectionally', async () => {
    // Create some local files
    const localDir = path.join(tempDir, 'local-only');
    await fs.mkdir(localDir, { recursive: true });
    await fs.writeFile(path.join(localDir, 'local.ts'), 'console.log("local file");');
    
    // Upload some files to the remote project
    await mockClient.uploadKnowledgeFile(projectId, 'remote-only/remote.ts', 'console.log("remote file");');
    
    // Sync bidirectionally
    await syncFiles('test-project', 'both');
    
    // Verify local file was uploaded
    const remoteFiles = await mockClient.listKnowledgeFiles(projectId);
    const uploadedLocal = remoteFiles.find(f => f.path === 'local-only/local.ts');
    expect(uploadedLocal).toBeDefined();
    expect(uploadedLocal?.content).toBe('console.log("local file");');
    
    // Verify remote file was downloaded
    const downloadedRemote = await fs.readFile(path.join(tempDir, 'remote-only/remote.ts'), 'utf-8');
    expect(downloadedRemote).toBe('console.log("remote file");');
  });
  
  it('should respect exclude patterns during upload', async () => {
    // Create files that should be excluded
    const nodeModulesDir = path.join(tempDir, 'node_modules');
    await fs.mkdir(nodeModulesDir, { recursive: true });
    await fs.writeFile(path.join(nodeModulesDir, 'package.js'), 'module.exports = {};');
    
    const gitDir = path.join(tempDir, '.git');
    await fs.mkdir(gitDir, { recursive: true });
    await fs.writeFile(path.join(gitDir, 'config'), '[core]');
    
    await fs.writeFile(path.join(tempDir, 'debug.log'), 'debug info');
    
    // Also create a file that should be included
    await fs.mkdir(path.join(tempDir, 'src'), { recursive: true });
    await fs.writeFile(path.join(tempDir, 'src/index.ts'), 'export default {};');
    
    // Sync files (upload only)
    await syncFiles('test-project', 'upload');
    
    // Verify only the allowed file was uploaded
    const uploadedFiles = await mockClient.listKnowledgeFiles(projectId);
    expect(uploadedFiles).toHaveLength(1);
    expect(uploadedFiles[0].path).toBe('src/index.ts');
  });
  
  it('should handle sync errors gracefully', async () => {
    // Mock the client to throw an error
    const errorClient = {
      ...mockClient,
      listKnowledgeFiles: vi.fn().mockRejectedValue(new Error('Network error')),
      uploadKnowledgeFile: vi.fn().mockRejectedValue(new Error('Upload failed'))
    };
    
    vi.mocked(ClaudeClientFactory.getClient).mockReturnValue(errorClient as any);
    
    // Create a test file
    await fs.writeFile(path.join(tempDir, 'test.ts'), 'test content');
    
    // Sync should throw the error now (changed behavior)
    await expect(syncFiles('test-project', 'both')).rejects.toThrow('Upload failed');
    
    // Verify error was logged
    expect(console.error).toHaveBeenCalledWith(
      expect.stringContaining('Synchronization failed'),
      expect.any(Error)
    );
  });
  
  it('should create directories as needed during download', async () => {
    // Upload a file with nested directory structure
    await mockClient.uploadKnowledgeFile(projectId, 'deep/nested/path/file.ts', 'export {};');
    
    // Sync files (download only)
    await syncFiles('test-project', 'download');
    
    // Verify the nested directory structure was created
    const filePath = path.join(tempDir, 'deep/nested/path/file.ts');
    const fileContent = await fs.readFile(filePath, 'utf-8');
    expect(fileContent).toBe('export {};');
    
    // Verify directories exist
    const stats = await fs.stat(path.join(tempDir, 'deep/nested/path'));
    expect(stats.isDirectory()).toBe(true);
  });
});