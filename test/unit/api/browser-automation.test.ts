/**
 * Tests for the ClaudeBrowserClient - browser automation for Claude.ai
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { ClaudeBrowserClient } from '../../../src/api/claude-browser-client.js';

describe('ClaudeBrowserClient', () => {
  let client: ClaudeBrowserClient;
  
  beforeEach(() => {
    vi.clearAllMocks();
    
    // Mock console methods to suppress output during tests
    vi.spyOn(console, 'log').mockImplementation(() => {});
    vi.spyOn(console, 'error').mockImplementation(() => {});
    
    // Create client with test credentials
    client = new ClaudeBrowserClient({
      email: 'test@example.com',
      password: 'testpassword'
    });
  });
  
  afterEach(() => {
    vi.restoreAllMocks();
  });
  
  it('should initialize with credentials', () => {
    const testClient = new ClaudeBrowserClient({
      email: 'user@test.com',
      password: 'secret123'
    });
    
    expect(testClient).toBeDefined();
    // Test that getCurrentUser reflects the provided email
    testClient.getCurrentUser().then(user => {
      expect(user.email).toBe('user@test.com');
    });
  });
  
  it('should initialize without credentials', () => {
    const noCredsClient = new ClaudeBrowserClient();
    expect(noCredsClient).toBeDefined();
  });
  
  it('should set credentials via setCredentials method', () => {
    const testClient = new ClaudeBrowserClient();
    testClient.setCredentials('new@example.com', 'newpassword');
    
    // Test that the credentials were set by calling getCurrentUser
    testClient.getCurrentUser().then(user => {
      expect(user.email).toBe('new@example.com');
    });
  });
  
  it('should throw error when trying to access projects without credentials', async () => {
    const noCredsClient = new ClaudeBrowserClient();
    
    await expect(noCredsClient.listProjects()).rejects.toThrow(
      'Login credentials are required for browser automation'
    );
  });
  
  it('should simulate login and list projects', async () => {
    const projects = await client.listProjects();
    
    expect(projects).toBeDefined();
    expect(Array.isArray(projects)).toBe(true);
    expect(projects.length).toBeGreaterThan(0);
    
    // Check project structure
    const project = projects[0];
    expect(project.id).toBeDefined();
    expect(project.name).toBeDefined();
    expect(project.ownerId).toBe('user-browser');
    expect(typeof project.isShared).toBe('boolean');
  });
  
  it('should get specific project details', async () => {
    // First get list of projects to get a valid ID
    const projects = await client.listProjects();
    const projectId = projects[0].id;
    
    const project = await client.getProject(projectId);
    
    expect(project).toBeDefined();
    expect(project.id).toBe(projectId);
    expect(project.knowledgeBase).toBeDefined();
    expect(project.knowledgeBase.fileCount).toBeGreaterThanOrEqual(0);
    expect(project.knowledgeBase.totalSizeBytes).toBeGreaterThanOrEqual(0);
  });
  
  it('should throw error for non-existent project', async () => {
    await expect(client.getProject('invalid-project-id')).rejects.toThrow(
      'Project with ID invalid-project-id not found'
    );
  });
  
  it('should list knowledge files for a project', async () => {
    const projects = await client.listProjects();
    const projectId = projects[0].id;
    
    const files = await client.listKnowledgeFiles(projectId);
    
    expect(files).toBeDefined();
    expect(Array.isArray(files)).toBe(true);
    
    if (files.length > 0) {
      const file = files[0];
      expect(file.id).toBeDefined();
      expect(file.name).toBeDefined();
      expect(file.path).toBeDefined();
      expect(typeof file.sizeBytes).toBe('number');
      expect(file.mimeType).toBeDefined();
      expect(file.createdAt).toBeDefined();
      expect(file.updatedAt).toBeDefined();
    }
  });
  
  it('should get specific knowledge file', async () => {
    const projects = await client.listProjects();
    const projectId = projects[0].id;
    
    const file = await client.getKnowledgeFile(projectId, 'test-file-id');
    
    expect(file).toBeDefined();
    expect(file.id).toBe('test-file-id');
    expect(file.name).toBeDefined();
    expect(file.content).toBeDefined();
    expect(typeof file.sizeBytes).toBe('number');
  });
  
  it('should upload a knowledge file', async () => {
    const projects = await client.listProjects();
    const projectId = projects[0].id;
    
    const testContent = 'This is test file content for upload';
    const testFilePath = 'test/upload/file.txt';
    
    const uploadedFile = await client.uploadKnowledgeFile(projectId, testFilePath, testContent);
    
    expect(uploadedFile).toBeDefined();
    expect(uploadedFile.id).toBeDefined();
    expect(uploadedFile.name).toBe('file.txt');
    expect(uploadedFile.path).toBe(testFilePath);
    expect(uploadedFile.content).toBe(testContent);
    expect(uploadedFile.sizeBytes).toBe(Buffer.from(testContent).length);
    expect(uploadedFile.mimeType).toBe('text/plain');
  });
  
  it('should upload a knowledge file with Buffer content', async () => {
    const projects = await client.listProjects();
    const projectId = projects[0].id;
    
    const testContent = Buffer.from('Binary test content', 'utf-8');
    const testFilePath = 'test/binary/data.bin';
    
    const uploadedFile = await client.uploadKnowledgeFile(projectId, testFilePath, testContent);
    
    expect(uploadedFile).toBeDefined();
    expect(uploadedFile.id).toBeDefined();
    expect(uploadedFile.name).toBe('data.bin');
    expect(uploadedFile.path).toBe(testFilePath);
    expect(uploadedFile.content).toBe(testContent.toString('utf-8'));
    expect(uploadedFile.sizeBytes).toBe(testContent.length);
  });
  
  it('should throw error when uploading to non-existent project', async () => {
    const testContent = 'test content';
    const testFilePath = 'test.txt';
    
    await expect(
      client.uploadKnowledgeFile('invalid-project', testFilePath, testContent)
    ).rejects.toThrow('Project with ID invalid-project not found');
  });
  
  it('should delete a knowledge file', async () => {
    const projects = await client.listProjects();
    const projectId = projects[0].id;
    
    // Should not throw
    await expect(
      client.deleteKnowledgeFile(projectId, 'test-file-id')
    ).resolves.not.toThrow();
  });
  
  it('should throw error when deleting from non-existent project', async () => {
    await expect(
      client.deleteKnowledgeFile('invalid-project', 'test-file-id')
    ).rejects.toThrow('Project with ID invalid-project not found');
  });
  
  it('should get current user information', async () => {
    const user = await client.getCurrentUser();
    
    expect(user).toBeDefined();
    expect(user.id).toBe('user-browser');
    expect(user.email).toBe('test@example.com');
    expect(user.name).toBe('Browser User');
    expect(user.accountType).toBe('plus');
  });
  
  it('should handle file path extraction correctly', async () => {
    const projects = await client.listProjects();
    const projectId = projects[0].id;
    
    // Test various file path formats
    const testCases = [
      { path: 'simple.txt', expectedName: 'simple.txt' },
      { path: 'folder/file.js', expectedName: 'file.js' },
      { path: 'deep/nested/path/document.md', expectedName: 'document.md' },
      { path: 'no-extension', expectedName: 'no-extension' }
    ];
    
    for (const testCase of testCases) {
      const uploadedFile = await client.uploadKnowledgeFile(
        projectId, 
        testCase.path, 
        'test content'
      );
      
      expect(uploadedFile.name).toBe(testCase.expectedName);
      expect(uploadedFile.path).toBe(testCase.path);
    }
  });
  
  it('should create sample projects on first access', async () => {
    const newClient = new ClaudeBrowserClient({
      email: 'fresh@example.com',
      password: 'password'
    });
    
    // First call should create sample projects
    const projects1 = await newClient.listProjects();
    expect(projects1.length).toBeGreaterThan(0);
    
    // Second call should return the same projects
    const projects2 = await newClient.listProjects();
    expect(projects2.length).toBe(projects1.length);
    expect(projects2[0].id).toBe(projects1[0].id);
  });
  
  it('should maintain login state across multiple calls', async () => {
    // Make multiple calls to verify login state is maintained
    const projects1 = await client.listProjects();
    const projects2 = await client.listProjects();
    const user = await client.getCurrentUser();
    
    // All calls should succeed without throwing login errors
    expect(projects1).toBeDefined();
    expect(projects2).toBeDefined();
    expect(user).toBeDefined();
    
    // Should have consistent data
    expect(projects2.length).toBe(projects1.length);
  });
});