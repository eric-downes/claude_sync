import { 
  ClaudeAPIClient, 
  ClaudeProject, 
  ClaudeProjectWithKnowledge, 
  ClaudeKnowledgeFile,
  ClaudeUser 
} from './interfaces.js';
import path from 'node:path';
import crypto from 'node:crypto';

/**
 * Mock implementation of the Claude API client for testing
 */
export class MockClaudeClient implements ClaudeAPIClient {
  private projects: Map<string, ClaudeProjectWithKnowledge>;
  private files: Map<string, Map<string, ClaudeKnowledgeFile>>;
  private user: ClaudeUser;
  
  constructor() {
    this.projects = new Map();
    this.files = new Map();
    
    // Create a mock user
    this.user = {
      id: 'user_mock123',
      email: 'test@example.com',
      name: 'Test User',
      accountType: 'plus'
    };
    
    // Add some mock projects
    this.addMockProject('Project 1', 'My first Claude project');
    this.addMockProject('Research Notes', 'Research and notes on AI topics');
    this.addMockProject('Code Examples', 'Programming examples and snippets');
  }
  
  /**
   * Add a mock project with basic data
   */
  private addMockProject(name: string, description: string): string {
    const now = new Date().toISOString();
    const id = 'proj_' + crypto.randomBytes(8).toString('hex');
    const knowledgeBaseId = 'kb_' + crypto.randomBytes(8).toString('hex');
    
    const project: ClaudeProjectWithKnowledge = {
      id,
      name,
      description,
      createdAt: now,
      updatedAt: now,
      ownerId: this.user.id,
      isShared: false,
      knowledgeBase: {
        id: knowledgeBaseId,
        fileCount: 0,
        totalSizeBytes: 0,
        lastUpdated: now
      }
    };
    
    this.projects.set(id, project);
    this.files.set(id, new Map());
    
    return id;
  }
  
  /**
   * List all projects
   */
  async listProjects(): Promise<ClaudeProject[]> {
    // Simulate network delay
    await new Promise(resolve => setTimeout(resolve, 300));
    
    return Array.from(this.projects.values());
  }
  
  /**
   * Get details of a specific project
   */
  async getProject(projectId: string): Promise<ClaudeProjectWithKnowledge> {
    // Simulate network delay
    await new Promise(resolve => setTimeout(resolve, 200));
    
    const project = this.projects.get(projectId);
    if (!project) {
      throw new Error(`Project with ID ${projectId} not found`);
    }
    
    return project;
  }
  
  /**
   * List all files in a project's knowledge base
   */
  async listKnowledgeFiles(projectId: string): Promise<ClaudeKnowledgeFile[]> {
    // Simulate network delay
    await new Promise(resolve => setTimeout(resolve, 400));
    
    const projectFiles = this.files.get(projectId);
    if (!projectFiles) {
      throw new Error(`Project with ID ${projectId} not found`);
    }
    
    return Array.from(projectFiles.values());
  }
  
  /**
   * Get a specific file from a project's knowledge base
   */
  async getKnowledgeFile(projectId: string, fileId: string): Promise<ClaudeKnowledgeFile> {
    // Simulate network delay
    await new Promise(resolve => setTimeout(resolve, 250));
    
    const projectFiles = this.files.get(projectId);
    if (!projectFiles) {
      throw new Error(`Project with ID ${projectId} not found`);
    }
    
    const file = projectFiles.get(fileId);
    if (!file) {
      throw new Error(`File with ID ${fileId} not found in project ${projectId}`);
    }
    
    return file;
  }
  
  /**
   * Upload a file to a project's knowledge base
   */
  async uploadKnowledgeFile(
    projectId: string, 
    filePath: string, 
    content: string | Buffer
  ): Promise<ClaudeKnowledgeFile> {
    // Simulate network delay
    await new Promise(resolve => setTimeout(resolve, 500));
    
    const project = this.projects.get(projectId);
    if (!project) {
      throw new Error(`Project with ID ${projectId} not found`);
    }
    
    const projectFiles = this.files.get(projectId);
    if (!projectFiles) {
      throw new Error(`Project files map for ${projectId} not found`);
    }
    
    const now = new Date().toISOString();
    const fileName = path.basename(filePath);
    const fileExtension = path.extname(filePath).toLowerCase();
    
    // Determine MIME type based on extension
    let mimeType = 'text/plain';
    if (fileExtension === '.pdf') mimeType = 'application/pdf';
    else if (fileExtension === '.docx') mimeType = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';
    else if (fileExtension === '.md') mimeType = 'text/markdown';
    else if (fileExtension === '.json') mimeType = 'application/json';
    else if (fileExtension === '.csv') mimeType = 'text/csv';
    else if (fileExtension === '.html') mimeType = 'text/html';
    
    // Create file object
    const fileId = 'file_' + crypto.randomBytes(8).toString('hex');
    const contentBuffer = typeof content === 'string' ? Buffer.from(content) : content;
    const sizeBytes = contentBuffer.length;
    
    const file: ClaudeKnowledgeFile = {
      id: fileId,
      name: fileName,
      path: filePath,
      sizeBytes,
      mimeType,
      createdAt: now,
      updatedAt: now,
      content: typeof content === 'string' ? content : contentBuffer.toString('utf-8')
    };
    
    // Add file to project
    projectFiles.set(fileId, file);
    
    // Update project metadata
    project.knowledgeBase.fileCount = projectFiles.size;
    project.knowledgeBase.totalSizeBytes += sizeBytes;
    project.knowledgeBase.lastUpdated = now;
    project.updatedAt = now;
    
    return file;
  }
  
  /**
   * Delete a file from a project's knowledge base
   */
  async deleteKnowledgeFile(projectId: string, fileId: string): Promise<void> {
    // Simulate network delay
    await new Promise(resolve => setTimeout(resolve, 350));
    
    const project = this.projects.get(projectId);
    if (!project) {
      throw new Error(`Project with ID ${projectId} not found`);
    }
    
    const projectFiles = this.files.get(projectId);
    if (!projectFiles) {
      throw new Error(`Project files map for ${projectId} not found`);
    }
    
    const file = projectFiles.get(fileId);
    if (!file) {
      throw new Error(`File with ID ${fileId} not found in project ${projectId}`);
    }
    
    // Delete file
    projectFiles.delete(fileId);
    
    // Update project metadata
    project.knowledgeBase.fileCount = projectFiles.size;
    project.knowledgeBase.totalSizeBytes -= file.sizeBytes;
    project.knowledgeBase.lastUpdated = new Date().toISOString();
    project.updatedAt = new Date().toISOString();
  }
  
  /**
   * Get the current authenticated user
   */
  async getCurrentUser(): Promise<ClaudeUser> {
    // Simulate network delay
    await new Promise(resolve => setTimeout(resolve, 150));
    
    return this.user;
  }
}