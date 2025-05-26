/**
 * Claude API Client
 * This is a placeholder file for testing purposes
 */

/**
 * Claude API client class
 */
export class ClaudeClient {
  constructor(config = {}) {
    this.config = config;
    this.projects = new Map();
    this.files = new Map();
    
    // Add some sample projects
    this.addSampleProject('Project 1', 'First project');
    this.addSampleProject('Project 2', 'Second project');
  }
  
  /**
   * Add a sample project
   */
  addSampleProject(name, description) {
    const id = `project-${this.projects.size + 1}`;
    const project = {
      id,
      name,
      description,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      knowledgeBase: {
        id: `kb-${id}`,
        fileCount: 0,
        totalSizeBytes: 0,
        lastUpdated: new Date().toISOString()
      }
    };
    
    this.projects.set(id, project);
    this.files.set(id, new Map());
    
    return project;
  }
  
  /**
   * List all projects
   */
  async listProjects() {
    return Array.from(this.projects.values());
  }
  
  /**
   * Get a specific project
   */
  async getProject(projectId) {
    const project = this.projects.get(projectId);
    if (!project) {
      throw new Error(`Project not found: ${projectId}`);
    }
    return project;
  }
  
  /**
   * List all files in a project
   */
  async listKnowledgeFiles(projectId) {
    const projectFiles = this.files.get(projectId);
    if (!projectFiles) {
      throw new Error(`Project not found: ${projectId}`);
    }
    return Array.from(projectFiles.values());
  }
  
  /**
   * Get a specific file from a project
   */
  async getKnowledgeFile(projectId, fileId) {
    const projectFiles = this.files.get(projectId);
    if (!projectFiles) {
      throw new Error(`Project not found: ${projectId}`);
    }
    
    const file = projectFiles.get(fileId);
    if (!file) {
      throw new Error(`File not found: ${fileId}`);
    }
    
    return file;
  }
  
  /**
   * Upload a file to a project
   */
  async uploadKnowledgeFile(projectId, fileName, content) {
    const project = this.projects.get(projectId);
    if (!project) {
      throw new Error(`Project not found: ${projectId}`);
    }
    
    const projectFiles = this.files.get(projectId);
    if (!projectFiles) {
      throw new Error(`Project files map not found: ${projectId}`);
    }
    
    const fileId = `file-${Date.now()}`;
    const file = {
      id: fileId,
      name: fileName,
      content,
      path: fileName,
      sizeBytes: content.length,
      mimeType: this.getMimeType(fileName),
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    };
    
    projectFiles.set(fileId, file);
    
    // Update project metadata
    project.knowledgeBase.fileCount = projectFiles.size;
    project.knowledgeBase.totalSizeBytes += content.length;
    project.knowledgeBase.lastUpdated = new Date().toISOString();
    project.updatedAt = new Date().toISOString();
    
    return file;
  }
  
  /**
   * Delete a file from a project
   */
  async deleteKnowledgeFile(projectId, fileId) {
    const project = this.projects.get(projectId);
    if (!project) {
      throw new Error(`Project not found: ${projectId}`);
    }
    
    const projectFiles = this.files.get(projectId);
    if (!projectFiles) {
      throw new Error(`Project files map not found: ${projectId}`);
    }
    
    const file = projectFiles.get(fileId);
    if (!file) {
      throw new Error(`File not found: ${fileId}`);
    }
    
    projectFiles.delete(fileId);
    
    // Update project metadata
    project.knowledgeBase.fileCount = projectFiles.size;
    project.knowledgeBase.totalSizeBytes -= file.sizeBytes;
    project.knowledgeBase.lastUpdated = new Date().toISOString();
    project.updatedAt = new Date().toISOString();
  }
  
  /**
   * Get MIME type based on file extension
   */
  getMimeType(fileName) {
    const extension = fileName.split('.').pop().toLowerCase();
    
    switch (extension) {
      case 'txt':
        return 'text/plain';
      case 'md':
        return 'text/markdown';
      case 'html':
        return 'text/html';
      case 'js':
        return 'application/javascript';
      case 'json':
        return 'application/json';
      case 'pdf':
        return 'application/pdf';
      case 'png':
        return 'image/png';
      case 'jpg':
      case 'jpeg':
        return 'image/jpeg';
      default:
        return 'application/octet-stream';
    }
  }
}