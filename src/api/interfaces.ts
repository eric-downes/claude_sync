/**
 * Interfaces for Claude AI API types
 */

// Project information returned from API
export interface ClaudeProject {
  id: string;
  name: string;
  description?: string;
  createdAt: string;
  updatedAt: string;
  ownerId: string;
  isShared: boolean;
}

// Project with additional information about knowledge base
export interface ClaudeProjectWithKnowledge extends ClaudeProject {
  knowledgeBase: {
    id: string;
    fileCount: number;
    totalSizeBytes: number;
    lastUpdated: string;
  };
}

// File in a project's knowledge base
export interface ClaudeKnowledgeFile {
  id: string;
  name: string;
  path: string;
  sizeBytes: number;
  mimeType: string;
  createdAt: string;
  updatedAt: string;
  content?: string;
  metadata?: Record<string, any>;
}

// User information
export interface ClaudeUser {
  id: string;
  email: string;
  name: string;
  accountType: 'free' | 'plus' | 'team' | 'enterprise';
}

// API client interface
export interface ClaudeAPIClient {
  // Project management
  listProjects(): Promise<ClaudeProject[]>;
  getProject(projectId: string): Promise<ClaudeProjectWithKnowledge>;
  
  // Knowledge base management
  listKnowledgeFiles(projectId: string): Promise<ClaudeKnowledgeFile[]>;
  getKnowledgeFile(projectId: string, fileId: string): Promise<ClaudeKnowledgeFile>;
  uploadKnowledgeFile(projectId: string, filePath: string, content: string | Buffer): Promise<ClaudeKnowledgeFile>;
  deleteKnowledgeFile(projectId: string, fileId: string): Promise<void>;
  
  // User management
  getCurrentUser(): Promise<ClaudeUser>;
}