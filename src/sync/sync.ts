import fs from 'fs/promises';
import path from 'path';
import { getProjectConfig, updateLastSynced } from '../config/configure.js';
import { uploadFileToProject, downloadFilesFromProject } from '../api/claude.js';

export type SyncDirection = 'upload' | 'download' | 'both';

// Main synchronization function
export async function syncFiles(projectName: string, direction: SyncDirection = 'both'): Promise<void> {
  try {
    // Get project configuration
    const projectConfig = getProjectConfig(projectName);
    if (!projectConfig) {
      throw new Error(`Project "${projectName}" not found. Please configure it first.`);
    }

    console.log(`Starting synchronization for project "${projectName}"...`);

    // Determine what to sync based on direction
    if (direction === 'upload' || direction === 'both') {
      await uploadLocalFiles(projectConfig);
    }

    if (direction === 'download' || direction === 'both') {
      await downloadProjectFiles(projectConfig);
    }

    // Update last synced timestamp
    updateLastSynced(projectName);
    console.log(`Synchronization completed for project "${projectName}".`);
  } catch (error) {
    console.error('Synchronization failed:', error);
  }
}

// Upload local files to Claude project
async function uploadLocalFiles(config: any): Promise<void> {
  const { localPath, projectId, excludePatterns } = config;

  console.log(`Uploading files from ${localPath} to project ${projectId}...`);

  try {
    // Get all files in the local directory
    const files = await getAllFiles(localPath, excludePatterns);
    
    console.log(`Found ${files.length} files to process.`);

    // Upload each file to the project
    for (const file of files) {
      const relativePath = path.relative(localPath, file);
      try {
        // Read file content
        const content = await fs.readFile(file, 'utf-8');
        
        // Upload to Claude project
        await uploadFileToProject(projectId, relativePath, content);
        console.log(`Uploaded: ${relativePath}`);
      } catch (error) {
        console.error(`Failed to upload ${relativePath}:`, error);
      }
    }
    
    console.log('Upload completed.');
  } catch (error) {
    console.error('Error during upload:', error);
  }
}

// Download files from Claude project to local directory
async function downloadProjectFiles(config: any): Promise<void> {
  const { localPath, projectId } = config;

  console.log(`Downloading files from project ${projectId} to ${localPath}...`);

  try {
    // Get files from Claude project
    const files = await downloadFilesFromProject(projectId);
    
    console.log(`Found ${files.length} files to download.`);

    // Save each file locally
    for (const file of files) {
      try {
        const filePath = path.join(localPath, file.name);
        
        // Ensure directory exists
        await fs.mkdir(path.dirname(filePath), { recursive: true });
        
        // Write file content
        await fs.writeFile(filePath, file.content || '');
        console.log(`Downloaded: ${file.name}`);
      } catch (error) {
        console.error(`Failed to save ${file.name}:`, error);
      }
    }
    
    console.log('Download completed.');
  } catch (error) {
    console.error('Error during download:', error);
  }
}

// Helper to recursively get all files in a directory
async function getAllFiles(dir: string, excludePatterns?: string[]): Promise<string[]> {
  const dirents = await fs.readdir(dir, { withFileTypes: true });
  
  const files = await Promise.all(dirents.map(async (dirent) => {
    const res = path.resolve(dir, dirent.name);
    
    // Check if the file matches exclude patterns
    if (excludePatterns && matchesAnyPattern(res, excludePatterns)) {
      return [];
    }
    
    return dirent.isDirectory() ? getAllFiles(res, excludePatterns) : [res];
  }));
  
  return files.flat();
}

// Check if a file path matches any of the exclude patterns
function matchesAnyPattern(filePath: string, patterns: string[]): boolean {
  const relativePath = path.basename(filePath);
  return patterns.some(pattern => {
    // Simple glob pattern matching
    if (pattern.startsWith('*') && pattern.endsWith('*')) {
      const middle = pattern.slice(1, -1);
      return relativePath.includes(middle);
    } else if (pattern.startsWith('*')) {
      const suffix = pattern.slice(1);
      return relativePath.endsWith(suffix);
    } else if (pattern.endsWith('*')) {
      const prefix = pattern.slice(0, -1);
      return relativePath.startsWith(prefix);
    } else {
      return relativePath === pattern || filePath.includes(`/${pattern}/`);
    }
  });
}