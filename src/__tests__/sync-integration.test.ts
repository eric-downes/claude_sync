import { describe, test, expect, jest, beforeEach } from '@jest/globals';
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import { syncFiles } from '../sync/sync.js';
import { ClaudeClientFactory } from '../api/client-factory.js';
import { MockClaudeClient } from '../api/mock-claude-client.js';
import * as configModule from '../config/configure.js';

// This test creates temporary directories and files to test syncing
// It uses the mock client to avoid real API calls

describe('Sync Integration', () => {
  let tempDir: string;
  let mockClient: MockClaudeClient;
  let projectId: string;
  
  // Mock the configuration module
  jest.mock('../config/configure.js', () => ({
    getProjectConfig: jest.fn(),
    updateLastSynced: jest.fn(),
    getAllProjects: jest.fn()
  }));
  
  // Mock the client factory to return our mock client
  jest.spyOn(ClaudeClientFactory, 'getClient').mockImplementation(() => mockClient);
  
  beforeEach(async () => {
    // Create a temp directory for test files
    tempDir = path.join(os.tmpdir(), `claude-sync-test-${Date.now()}`);
    await fs.mkdir(tempDir, { recursive: true });
    
    // Create a mock client
    mockClient = new MockClaudeClient();
    
    // Get a project ID from the mock client
    const projects = await mockClient.listProjects();
    projectId = projects[0].id;
    
    // Setup mock project config
    (configModule.getProjectConfig as jest.Mock).mockReturnValue({
      projectId,
      projectName: 'Test Project',
      localPath: tempDir,
      excludePatterns: ['node_modules', '*.log']
    });
  });
  
  afterEach(async () => {
    // Clean up temp directory
    await fs.rm(tempDir, { recursive: true, force: true });
    jest.resetAllMocks();
  });
  
  test('should upload local files to Claude project', async () => {
    // Create test files
    const file1Path = path.join(tempDir, 'test1.txt');
    const file2Path = path.join(tempDir, 'test2.md');
    const subdirPath = path.join(tempDir, 'subdir');
    const file3Path = path.join(subdirPath, 'test3.json');
    
    await fs.writeFile(file1Path, 'Test file 1 content');
    await fs.writeFile(file2Path, 'Test file 2 content');
    await fs.mkdir(subdirPath, { recursive: true });
    await fs.writeFile(file3Path, '{"key": "Test file 3 content"}');
    
    // Create a file that should be excluded
    await fs.writeFile(path.join(tempDir, 'test.log'), 'This should be excluded');
    
    // Sync files (upload direction)
    await syncFiles('Test Project', 'upload');
    
    // Verify files were uploaded
    const files = await mockClient.listKnowledgeFiles(projectId);
    expect(files.length).toBe(3); // Excluding the .log file
    
    // Verify file names
    const fileNames = files.map(f => f.name);
    expect(fileNames.includes('test1.txt')).toBe(true);
    expect(fileNames.includes('test2.md')).toBe(true);
    expect(fileNames.includes('test3.json')).toBe(true);
    expect(fileNames.includes('test.log')).toBe(false); // Should be excluded
    
    // Verify file contents (one is enough for the test)
    const testFile = files.find(f => f.name === 'test1.txt');
    if (testFile) {
      const fileContent = await mockClient.getKnowledgeFile(projectId, testFile.id);
      expect(fileContent.content).toBe('Test file 1 content');
    }
  });
  
  test('should download files from Claude project to local directory', async () => {
    // Upload test files to the mock project
    await mockClient.uploadKnowledgeFile(projectId, 'download1.txt', 'Download test 1');
    await mockClient.uploadKnowledgeFile(projectId, 'download2.md', 'Download test 2');
    
    // Sync files (download direction)
    await syncFiles('Test Project', 'download');
    
    // Verify files were downloaded
    const file1Content = await fs.readFile(path.join(tempDir, 'download1.txt'), 'utf-8');
    const file2Content = await fs.readFile(path.join(tempDir, 'download2.md'), 'utf-8');
    
    expect(file1Content).toBe('Download test 1');
    expect(file2Content).toBe('Download test 2');
  });
  
  test('should sync bidirectionally', async () => {
    // Create a local file
    const localFilePath = path.join(tempDir, 'local.txt');
    await fs.writeFile(localFilePath, 'Local file content');
    
    // Upload a file to the mock project
    await mockClient.uploadKnowledgeFile(projectId, 'remote.txt', 'Remote file content');
    
    // Sync files (both directions)
    await syncFiles('Test Project', 'both');
    
    // Verify local file was uploaded
    const projectFiles = await mockClient.listKnowledgeFiles(projectId);
    const localFileInProject = projectFiles.find(f => f.name === 'local.txt');
    expect(localFileInProject).toBeDefined();
    
    // Verify remote file was downloaded
    const remoteFileContent = await fs.readFile(path.join(tempDir, 'remote.txt'), 'utf-8');
    expect(remoteFileContent).toBe('Remote file content');
  });
});