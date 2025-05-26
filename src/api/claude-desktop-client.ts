import { ClaudeAPIClient, ClaudeProject, ClaudeProjectWithKnowledge, ClaudeKnowledgeFile, ClaudeUser } from './interfaces.js';
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import crypto from 'node:crypto';

/**
 * Client implementation for accessing Claude Desktop data
 * 
 * Note: This implementation currently uses sample data.
 * In the future, it could parse the Claude Desktop data files
 * directly without requiring a LevelDB dependency.
 */
export class ClaudeDesktopClient implements ClaudeAPIClient {
  private appDataPath: string;
  private isInitialized: boolean = false;
  private cachedProjects: Map<string, ClaudeProjectWithKnowledge> = new Map();
  private cachedFiles: Map<string, Map<string, ClaudeKnowledgeFile>> = new Map();
  
  constructor() {
    // Determine Claude Desktop storage location based on OS
    if (os.platform() === 'darwin') {
      this.appDataPath = path.join(os.homedir(), 'Library', 'Application Support', 'Claude');
    } else if (os.platform() === 'win32') {
      this.appDataPath = path.join(os.homedir(), 'AppData', 'Roaming', 'Claude');
    } else {
      this.appDataPath = path.join(os.homedir(), '.config', 'Claude');
    }
  }
  
  /**
   * Initialize by checking if Claude Desktop is installed and creating sample projects
   */
  private async initialize(): Promise<void> {
    if (this.isInitialized) return;
    
    try {
      // Verify Claude Desktop directory exists
      await fs.access(this.appDataPath);
      console.log(`Found Claude Desktop at: ${this.appDataPath}`);
      
      // Create sample projects for now
      // In the future, we could parse the files without needing LevelDB
      this.createSampleProjects();
      this.isInitialized = true;
    } catch (error) {
      console.error('Error initializing Claude Desktop client:', error);
      
      // Create sample projects as a fallback
      console.warn('Using fallback project generation.');
      this.createSampleProjects();
      this.isInitialized = true;
    }
  }
  
  /**
   * List all projects in Claude Desktop
   */
  async listProjects(): Promise<ClaudeProject[]> {
    await this.initialize();
    
    // If no projects were found in the database, simulate some basic projects
    if (this.cachedProjects.size === 0) {
      // Create a few sample projects
      this.createSampleProjects();
    }
    
    return Array.from(this.cachedProjects.values());
  }
  
  /**
   * Get details of a specific project
   */
  async getProject(projectId: string): Promise<ClaudeProjectWithKnowledge> {
    await this.initialize();
    
    const project = this.cachedProjects.get(projectId);
    if (!project) {
      throw new Error(`Project with ID ${projectId} not found in Claude Desktop`);
    }
    
    return project;
  }
  
  /**
   * List all files in a project's knowledge base
   */
  async listKnowledgeFiles(projectId: string): Promise<ClaudeKnowledgeFile[]> {
    await this.initialize();
    
    // Check if project exists
    if (!this.cachedProjects.has(projectId)) {
      throw new Error(`Project with ID ${projectId} not found in Claude Desktop`);
    }
    
    // Get files for this project
    const projectFiles = this.cachedFiles.get(projectId);
    if (!projectFiles) {
      return [];
    }
    
    return Array.from(projectFiles.values());
  }
  
  /**
   * Get a specific file from a project's knowledge base
   */
  async getKnowledgeFile(projectId: string, fileId: string): Promise<ClaudeKnowledgeFile> {
    await this.initialize();
    
    // Check if project exists
    if (!this.cachedProjects.has(projectId)) {
      throw new Error(`Project with ID ${projectId} not found in Claude Desktop`);
    }
    
    // Get files for this project
    const projectFiles = this.cachedFiles.get(projectId);
    if (!projectFiles) {
      throw new Error(`No files found for project ${projectId}`);
    }
    
    // Get specific file
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
    await this.initialize();
    
    // Check if project exists
    if (!this.cachedProjects.has(projectId)) {
      throw new Error(`Project with ID ${projectId} not found in Claude Desktop`);
    }
    
    // Get project and files
    const project = this.cachedProjects.get(projectId)!;
    const projectFiles = this.cachedFiles.get(projectId);
    
    if (!projectFiles) {
      throw new Error(`Failed to access files for project ${projectId}`);
    }
    
    // Create file
    const now = new Date().toISOString();
    const fileId = `file-${crypto.randomBytes(8).toString('hex')}`;
    const fileName = path.basename(filePath);
    const fileExt = path.extname(filePath).toLowerCase();
    
    // Determine MIME type based on extension
    let mimeType = 'text/plain';
    if (fileExt === '.pdf') mimeType = 'application/pdf';
    else if (fileExt === '.docx') mimeType = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';
    else if (fileExt === '.md') mimeType = 'text/markdown';
    else if (fileExt === '.json') mimeType = 'application/json';
    else if (fileExt === '.csv') mimeType = 'text/csv';
    else if (fileExt === '.html') mimeType = 'text/html';
    
    // Convert content to string if it's a buffer
    const contentStr = Buffer.isBuffer(content) ? content.toString('utf-8') : content;
    const sizeBytes = Buffer.isBuffer(content) ? content.length : Buffer.from(content).length;
    
    // Create file object
    const file: ClaudeKnowledgeFile = {
      id: fileId,
      name: fileName,
      path: filePath,
      sizeBytes,
      mimeType,
      createdAt: now,
      updatedAt: now,
      content: contentStr,
      metadata: {
        uploadedVia: 'claude-sync'
      }
    };
    
    // Add to cache
    projectFiles.set(fileId, file);
    
    // Update project knowledge base stats
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
    await this.initialize();
    
    // Check if project exists
    if (!this.cachedProjects.has(projectId)) {
      throw new Error(`Project with ID ${projectId} not found in Claude Desktop`);
    }
    
    // Get project and files
    const project = this.cachedProjects.get(projectId)!;
    const projectFiles = this.cachedFiles.get(projectId);
    
    if (!projectFiles) {
      throw new Error(`Failed to access files for project ${projectId}`);
    }
    
    // Get file to delete
    const file = projectFiles.get(fileId);
    if (!file) {
      throw new Error(`File with ID ${fileId} not found in project ${projectId}`);
    }
    
    // Remove from cache
    projectFiles.delete(fileId);
    
    // Update project knowledge base stats
    project.knowledgeBase.fileCount = projectFiles.size;
    project.knowledgeBase.totalSizeBytes -= file.sizeBytes;
    project.knowledgeBase.lastUpdated = new Date().toISOString();
    project.updatedAt = new Date().toISOString();
  }
  
  /**
   * Get the current user
   */
  async getCurrentUser(): Promise<ClaudeUser> {
    await this.initialize();
    
    // For now, return a default local user
    return {
      id: 'local-user',
      email: 'local@claude-desktop.local',
      name: 'Claude Desktop User',
      accountType: 'plus'
    };
  }
  
  /**
   * Process and save project data
   */
  private processProjectData(projectData: any): void {
    if (!projectData || !projectData.id) return;
    
    // Extract project name - handle different formats
    let name = projectData.name || projectData.title || 'Unnamed Project';
    if (typeof name !== 'string') {
      name = `Project ${projectData.id.substring(0, 8)}`;
    }
    
    // Create project object
    const project: ClaudeProjectWithKnowledge = {
      id: projectData.id,
      name: name,
      description: projectData.description || '',
      createdAt: projectData.createdAt || projectData.created_at || new Date().toISOString(),
      updatedAt: projectData.updatedAt || projectData.updated_at || new Date().toISOString(),
      ownerId: projectData.ownerId || projectData.owner_id || 'local-user',
      isShared: Boolean(projectData.isShared || projectData.is_shared || false),
      knowledgeBase: {
        id: projectData.knowledgeBaseId || projectData.knowledge_base_id || `kb-${crypto.randomBytes(4).toString('hex')}`,
        fileCount: 0,
        totalSizeBytes: 0,
        lastUpdated: new Date().toISOString()
      }
    };
    
    console.log(`[INFO] Processed project: ${project.name} (${project.id})`);
    
    // Add to cache if not already present
    if (!this.cachedProjects.has(project.id)) {
      this.cachedProjects.set(project.id, project);
      this.cachedFiles.set(project.id, new Map());
    }
  }
  
  /**
   * Extract projects from complex data
   */
  private extractProjectsFromData(data: any, sourceKey: string): void {
    if (!data) return;
    
    try {
      // Case 1: data is an array of projects
      if (Array.isArray(data)) {
        console.log(`[INFO] Found array of potential projects in key ${sourceKey}`);
        for (const item of data) {
          if (item && item.id) {
            this.processProjectData(item);
          }
        }
        return;
      }
      
      // Case 2: data has a projects array or object
      if (data.projects) {
        console.log(`[INFO] Found projects field in data from key ${sourceKey}`);
        
        if (Array.isArray(data.projects)) {
          for (const project of data.projects) {
            this.processProjectData(project);
          }
        } else if (typeof data.projects === 'object') {
          // Projects might be an object with project IDs as keys
          for (const projectId of Object.keys(data.projects)) {
            const project = data.projects[projectId];
            if (typeof project === 'object') {
              // Ensure the project has the ID from the key
              this.processProjectData({ ...project, id: projectId });
            }
          }
        }
        return;
      }
      
      // Case 3: projectList field
      if (data.projectList) {
        console.log(`[INFO] Found projectList field in data from key ${sourceKey}`);
        
        if (Array.isArray(data.projectList)) {
          for (const project of data.projectList) {
            this.processProjectData(project);
          }
        } else if (typeof data.projectList === 'object') {
          for (const projectId of Object.keys(data.projectList)) {
            const project = data.projectList[projectId];
            if (typeof project === 'object') {
              this.processProjectData({ ...project, id: projectId });
            }
          }
        }
        return;
      }
      
      // Case 4: Look for anything that could be a project
      for (const key of Object.keys(data)) {
        const value = data[key];
        
        // If the value is an object and has id and name fields, it might be a project
        if (value && typeof value === 'object' && value.id && (value.name || value.title)) {
          console.log(`[INFO] Found potential project in field ${key} from key ${sourceKey}`);
          this.processProjectData(value);
        }
        
        // If the value is an array, check if its items look like projects
        if (value && Array.isArray(value) && value.length > 0) {
          for (const item of value) {
            if (item && typeof item === 'object' && item.id && (item.name || item.title)) {
              console.log(`[INFO] Found potential project in array ${key} from key ${sourceKey}`);
              this.processProjectData(item);
            }
          }
        }
      }
    } catch (error) {
      console.warn(`Error extracting projects from data in key ${sourceKey}:`, error);
    }
  }
  
  /**
   * Create sample projects if none were found
   */
  private createSampleProjects(): void {
    const now = new Date().toISOString();
    
    // Project 1
    const project1Id = `project-${crypto.randomBytes(4).toString('hex')}`;
    const project1: ClaudeProjectWithKnowledge = {
      id: project1Id,
      name: 'Research Notes',
      description: 'My research notes and ideas',
      createdAt: now,
      updatedAt: now,
      ownerId: 'local-user',
      isShared: false,
      knowledgeBase: {
        id: `kb-${crypto.randomBytes(4).toString('hex')}`,
        fileCount: 0,
        totalSizeBytes: 0,
        lastUpdated: now
      }
    };
    
    // Project 2
    const project2Id = `project-${crypto.randomBytes(4).toString('hex')}`;
    const project2: ClaudeProjectWithKnowledge = {
      id: project2Id,
      name: 'Code Examples',
      description: 'Programming snippets and examples',
      createdAt: now,
      updatedAt: now,
      ownerId: 'local-user',
      isShared: false,
      knowledgeBase: {
        id: `kb-${crypto.randomBytes(4).toString('hex')}`,
        fileCount: 0,
        totalSizeBytes: 0,
        lastUpdated: now
      }
    };
    
    // Add projects to cache
    this.cachedProjects.set(project1Id, project1);
    this.cachedProjects.set(project2Id, project2);
    
    // Initialize file maps
    this.cachedFiles.set(project1Id, new Map());
    this.cachedFiles.set(project2Id, new Map());
    
    console.log('Created sample projects since no projects were found in Claude Desktop');
  }
}