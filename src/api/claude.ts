import { getApiKey } from '../config/configure.js';
import Anthropic from '@anthropic-ai/sdk';
import { ClaudeClientFactory } from './client-factory.js';
import { ClaudeKnowledgeFile } from './interfaces.js';

// Use ClaudeKnowledgeFile instead of this simplified interface
interface ProjectFile {
  name: string;
  content: string;
  lastModified: Date;
}

// Initialize Anthropic client for text generation
function getAnthropicClient(): Anthropic {
  const apiKey = getApiKey();
  if (!apiKey) {
    throw new Error('API key not found. Please configure it using the config command.');
  }
  
  return new Anthropic({
    apiKey
  });
}

// Get Claude API client for project operations
function getClaudeClient() {
  return ClaudeClientFactory.getClient();
}

// Upload a file to Claude project
export async function uploadFileToProject(
  projectId: string,
  filePath: string,
  content: string
): Promise<void> {
  console.log(`Uploading ${filePath} to project ${projectId}`);

  try {
    const client = getClaudeClient();
    await client.uploadKnowledgeFile(projectId, filePath, content);
    console.log(`File ${filePath} uploaded to project ${projectId}`);
  } catch (error) {
    console.error(`Error uploading file ${filePath} to project ${projectId}:`, error);
    throw error;
  }
}

// Download files from Claude project
export async function downloadFilesFromProject(projectId: string): Promise<ClaudeKnowledgeFile[]> {
  console.log(`Downloading files from project ${projectId}`);

  try {
    const client = getClaudeClient();
    const files = await client.listKnowledgeFiles(projectId);
    
    // Load content for each file
    const filesWithContent: ClaudeKnowledgeFile[] = [];
    
    for (const file of files) {
      const fileWithContent = await client.getKnowledgeFile(projectId, file.id);
      filesWithContent.push(fileWithContent);
    }
    
    return filesWithContent;
  } catch (error) {
    console.error(`Error downloading files from project ${projectId}:`, error);
    throw error;
  }
}

// Check if a project exists
export async function projectExists(projectId: string): Promise<boolean> {
  try {
    const client = getClaudeClient();
    await client.getProject(projectId);
    return true;
  } catch (error) {
    console.error(`Error checking project existence:`, error);
    return false;
  }
}

// Get project details
export async function getProjectDetails(projectId: string): Promise<any> {
  try {
    const client = getClaudeClient();
    return await client.getProject(projectId);
  } catch (error) {
    console.error(`Error getting project details:`, error);
    throw error;
  }
}

// List all user's projects
export async function listAllProjects(): Promise<any[]> {
  try {
    const client = getClaudeClient();
    return await client.listProjects();
  } catch (error) {
    console.error(`Error listing projects:`, error);
    throw error;
  }
}