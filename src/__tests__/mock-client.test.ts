import { describe, it, expect, beforeEach } from 'vitest';
import { MockClaudeClient } from '../api/mock-claude-client.js';
import { ClaudeKnowledgeFile } from '../api/interfaces.js';

describe('MockClaudeClient', () => {
  let client: MockClaudeClient;
  let projects: any[];
  let projectId: string;

  beforeEach(async () => {
    client = new MockClaudeClient();
    projects = await client.listProjects();
    projectId = projects[0].id;
  });

  it('should list projects', async () => {
    const projects = await client.listProjects();
    expect(projects).toBeDefined();
    expect(projects.length).toBeGreaterThan(0);
    expect(projects[0].name).toBeDefined();
    expect(projects[0].id).toBeDefined();
  });

  it('should get project details', async () => {
    const project = await client.getProject(projectId);
    expect(project).toBeDefined();
    expect(project.id).toBe(projectId);
    expect(project.name).toBeDefined();
    expect(project.knowledgeBase).toBeDefined();
  });

  it('should initially have no files in a project', async () => {
    const files = await client.listKnowledgeFiles(projectId);
    expect(files).toBeDefined();
    expect(files.length).toBe(0);
  });

  it('should upload a file to project', async () => {
    // Upload a test file
    const file = await client.uploadKnowledgeFile(
      projectId, 
      'test.txt', 
      'This is a test file content'
    );
    
    expect(file).toBeDefined();
    expect(file.id).toBeDefined();
    expect(file.name).toBe('test.txt');
    expect(file.content).toBe('This is a test file content');
    
    // Verify the file is in the project
    const files = await client.listKnowledgeFiles(projectId);
    expect(files.length).toBe(1);
    expect(files[0].id).toBe(file.id);
  });

  it('should download file content', async () => {
    // Upload a test file
    const uploadedFile = await client.uploadKnowledgeFile(
      projectId, 
      'download-test.txt', 
      'Content for download test'
    );
    
    // Get the file content
    const file = await client.getKnowledgeFile(projectId, uploadedFile.id);
    expect(file).toBeDefined();
    expect(file.content).toBe('Content for download test');
  });

  it('should delete a file', async () => {
    // Upload a test file
    const file = await client.uploadKnowledgeFile(
      projectId, 
      'delete-test.txt', 
      'This file will be deleted'
    );
    
    // Verify file exists
    let files = await client.listKnowledgeFiles(projectId);
    const initialCount = files.length;
    expect(files.some(f => f.id === file.id)).toBe(true);
    
    // Delete the file
    await client.deleteKnowledgeFile(projectId, file.id);
    
    // Verify file is deleted
    files = await client.listKnowledgeFiles(projectId);
    expect(files.length).toBe(initialCount - 1);
    expect(files.some(f => f.id === file.id)).toBe(false);
  });

  it('should throw error when accessing non-existent project', async () => {
    await expect(client.getProject('invalid-id')).rejects.toThrow();
    await expect(client.listKnowledgeFiles('invalid-id')).rejects.toThrow();
  });

  it('should throw error when accessing non-existent file', async () => {
    await expect(client.getKnowledgeFile(projectId, 'invalid-file')).rejects.toThrow();
    await expect(client.deleteKnowledgeFile(projectId, 'invalid-file')).rejects.toThrow();
  });
});