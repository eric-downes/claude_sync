import fs from 'node:fs';
import path from 'node:path';
import { uploadFileToProject } from '../api/claude.js';
import { getProjectConfig } from '../config/configure.js';
import { readFile } from 'node:fs/promises';

/**
 * Watch a project's directory for file changes and sync to Claude AI project
 */
export async function watchProject(projectName: string): Promise<() => void> {
  const projectConfig = getProjectConfig(projectName);
  if (!projectConfig) {
    throw new Error(`Project "${projectName}" not found. Please configure it first.`);
  }

  const { localPath, projectId, excludePatterns } = projectConfig;
  const resolvedPath = path.resolve(localPath);
  
  console.log(`Starting file watcher for project "${projectName}" at ${resolvedPath}`);
  
  // Set up file watcher
  const watcher = fs.watch(resolvedPath, { recursive: true }, async (eventType, filename) => {
    if (!filename) return;
    
    const fullPath = path.resolve(resolvedPath, filename);
    const relativePath = path.relative(resolvedPath, fullPath);
    
    // Check if file matches exclude patterns
    if (excludePatterns && matchesAnyPattern(relativePath, excludePatterns)) {
      return;
    }
    
    console.log(`File ${relativePath} changed (${eventType})`);
    
    try {
      // Read the file content
      const content = await readFile(fullPath, 'utf-8');
      
      // Upload to Claude project
      await uploadFileToProject(projectId, relativePath, content);
      console.log(`Synced ${relativePath} to project ${projectId}`);
    } catch (error) {
      console.error(`Error syncing ${relativePath}:`, error);
    }
  });
  
  // Return a function to stop watching
  return () => {
    watcher.close();
    console.log(`Stopped file watcher for project "${projectName}"`);
  };
}

// Check if a file path matches any of the exclude patterns
function matchesAnyPattern(filePath: string, patterns: string[]): boolean {
  return patterns.some(pattern => {
    // Simple glob pattern matching
    if (pattern.startsWith('*') && pattern.endsWith('*')) {
      const middle = pattern.slice(1, -1);
      return filePath.includes(middle);
    } else if (pattern.startsWith('*')) {
      const suffix = pattern.slice(1);
      return filePath.endsWith(suffix);
    } else if (pattern.endsWith('*')) {
      const prefix = pattern.slice(0, -1);
      return filePath.startsWith(prefix);
    } else {
      return filePath === pattern || filePath.includes(`/${pattern}/`);
    }
  });
}