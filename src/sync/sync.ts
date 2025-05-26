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
    throw error; // Re-throw for proper error handling in tests and CLI
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
        throw error; // Re-throw for proper error handling
      }
    }
    
    console.log('Upload completed.');
  } catch (error) {
    console.error('Error during upload:', error);
    throw error; // Re-throw for proper error handling
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
        const filePath = path.join(localPath, file.path);
        
        // Ensure directory exists
        await fs.mkdir(path.dirname(filePath), { recursive: true });
        
        // Write file content
        await fs.writeFile(filePath, file.content || '');
        console.log(`Downloaded: ${file.path}`);
      } catch (error) {
        console.error(`Failed to save ${file.path}:`, error);
        throw error; // Re-throw for proper error handling
      }
    }
    
    console.log('Download completed.');
  } catch (error) {
    console.error('Error during download:', error);
    throw error; // Re-throw for proper error handling
  }
}

// Helper to recursively get all files in a directory
async function getAllFiles(dir: string, excludePatterns?: string[], baseDir?: string): Promise<string[]> {
  const actualBaseDir = baseDir || dir;
  const dirents = await fs.readdir(dir, { withFileTypes: true });
  
  const files = await Promise.all(dirents.map(async (dirent) => {
    const res = path.resolve(dir, dirent.name);
    
    // Check if the file matches exclude patterns
    if (excludePatterns && matchesAnyPattern(res, excludePatterns, actualBaseDir)) {
      return [];
    }
    
    return dirent.isDirectory() ? getAllFiles(res, excludePatterns, actualBaseDir) : [res];
  }));
  
  return files.flat();
}

// Check if a file path matches any of the exclude patterns
function matchesAnyPattern(filePath: string, patterns: string[], baseDir: string): boolean {
  // Get relative path from base directory for pattern matching
  const relativePath = path.relative(baseDir, filePath);
  const normalizedPath = relativePath.replace(/\\/g, '/'); // Normalize to forward slashes
  
  return patterns.some(pattern => {
    // Handle different glob patterns
    if (pattern.endsWith('/**')) {
      // Directory patterns like "node_modules/**"
      const dirName = pattern.slice(0, -3);
      return normalizedPath.startsWith(dirName + '/') || normalizedPath === dirName;
    } else if (pattern.startsWith('*')) {
      // File extension patterns like "*.log"
      const suffix = pattern.slice(1);
      return normalizedPath.endsWith(suffix);
    } else if (pattern.endsWith('*')) {
      // Prefix patterns
      const prefix = pattern.slice(0, -1);
      return normalizedPath.startsWith(prefix);
    } else {
      // Exact match
      return normalizedPath === pattern || normalizedPath.includes('/' + pattern + '/');
    }
  });
}