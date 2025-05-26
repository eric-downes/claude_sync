import path from 'node:path';
import fs from 'node:fs/promises';
import { listAllProjects, downloadFilesFromProject } from '../api/claude.js';
import { configureProject, getProjectConfig, updateLastSynced, addProjectConfig } from '../config/configure.js';
import { syncFiles } from './sync.js';
import { SyncDirection } from './sync.js';

interface SyncAllOptions {
  baseDir: string;
  direction: SyncDirection;
  forceConfig?: boolean;
}

/**
 * Synchronize all Claude AI projects to subdirectories
 */
export async function syncAllProjects(options: SyncAllOptions): Promise<void> {
  const { baseDir, direction, forceConfig = false } = options;
  
  try {
    // List all projects
    console.log('Fetching list of Claude AI projects...');
    const projects = await listAllProjects();
    console.log(`Found ${projects.length} projects.`);
    
    // Ensure base directory exists
    await fs.mkdir(baseDir, { recursive: true });
    
    // Process each project
    for (const project of projects) {
      // Create a sanitized directory name for the project
      const dirName = project.name.replace(/[^a-zA-Z0-9_-]/g, '_');
      const projectDir = path.join(baseDir, dirName);
      
      console.log(`\nProcessing project "${project.name}" (${project.id})`);
      
      // Check if project is already configured
      let projectConfig = getProjectConfig(project.name);
      
      if (!projectConfig || forceConfig) {
        // Create directory for the project
        console.log(`Creating directory ${projectDir}...`);
        await fs.mkdir(projectDir, { recursive: true });
        
        // Configure the project
        console.log(`Configuring project ${project.name}...`);
        await configureProjectAutomatically(project.name, project.id, projectDir);
        
        // Refresh the config
        projectConfig = getProjectConfig(project.name);
      }
      
      if (projectConfig) {
        // Sync the project
        console.log(`Syncing project ${project.name}...`);
        await syncFiles(project.name, direction);
      } else {
        console.error(`Could not configure project ${project.name}. Skipping sync.`);
      }
    }
    
    console.log('\nAll projects synchronized successfully.');
  } catch (error) {
    console.error('Error synchronizing all projects:', error);
    throw error;
  }
}

/**
 * Automatically configure a project without user interaction
 */
async function configureProjectAutomatically(
  projectName: string,
  projectId: string,
  localPath: string
): Promise<void> {
  // Create project configuration
  const projectConfig = {
    projectId,
    projectName,
    localPath,
    excludePatterns: ['node_modules', '.git', '*.log'],
    lastSynced: new Date()
  };
  
  // Save configuration
  await saveProjectConfig(projectName, projectConfig);
  
  console.log(`Project "${projectName}" configured automatically.`);
}

/**
 * Save project configuration
 */
async function saveProjectConfig(projectName: string, config: any): Promise<void> {
  addProjectConfig(projectName, config);
  updateLastSynced(projectName);
}