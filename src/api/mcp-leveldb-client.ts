/**
 * Example integration of LevelDB MCP with claude-desktop-client
 * This file shows how to use the LevelDB MCP to access Claude Desktop data
 */

import { ClaudeDesktopClient } from './claude-desktop-client.js';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';

export class LevelDBDesktopClient extends ClaudeDesktopClient {
  private mcpPort: number = 3000;
  
  constructor(mcpPort?: number) {
    super();
    if (mcpPort) {
      this.mcpPort = mcpPort;
    }
  }
  
  /**
   * Initialize by reading real data from Claude Desktop LevelDB
   */
  protected async initialize(): Promise<void> {
    if (this.isInitialized) return;
    
    try {
      // Determine Claude Desktop path based on OS
      const appDataPath = this._getClaudeDesktopPath();
      console.log(`Found Claude Desktop at: ${appDataPath}`);
      
      // Access the LevelDB database through MCP
      const leveldbPath = path.join(appDataPath, 'Local Storage', 'leveldb');
      await this._readProjects(leveldbPath);
      
      this.isInitialized = true;
    } catch (error) {
      console.error('Error reading Claude Desktop data:', error);
      
      // Fall back to creating sample projects
      console.warn('Falling back to sample projects.');
      await super.initialize();
    }
  }
  
  /**
   * Get Claude Desktop path based on OS
   */
  private _getClaudeDesktopPath(): string {
    if (os.platform() === 'darwin') {
      return path.join(os.homedir(), 'Library', 'Application Support', 'Claude');
    } else if (os.platform() === 'win32') {
      return path.join(os.homedir(), 'AppData', 'Roaming', 'Claude');
    } else {
      return path.join(os.homedir(), '.config', 'Claude');
    }
  }
  
  /**
   * Read projects from LevelDB using MCP
   */
  private async _readProjects(leveldbPath: string): Promise<void> {
    try {
      // Find project related data in LevelDB
      console.log(`Reading projects from LevelDB at ${leveldbPath}`);
      
      // First, look for keys with "project" in them
      const mcpResponse = await fetch(`http://localhost:${this.mcpPort}/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          action: 'leveldb-keys',
          parameters: {
            dbPath: leveldbPath,
            prefix: 'project'
          }
        })
      });
      
      const keysResult = await mcpResponse.json();
      if (keysResult.status !== 'success' || !keysResult.data?.keys?.length) {
        console.warn('No project keys found in LevelDB');
        // Fall back to sample projects
        this._createSampleProjects();
        return;
      }
      
      console.log(`Found ${keysResult.data.keys.length} project-related keys in LevelDB`);
      
      // Read each key's data
      let foundProjects = false;
      for (const key of keysResult.data.keys) {
        const dataResponse = await fetch(`http://localhost:${this.mcpPort}/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            action: 'leveldb-get',
            parameters: {
              dbPath: leveldbPath,
              key
            }
          })
        });
        
        const dataResult = await dataResponse.json();
        if (dataResult.status === 'success' && dataResult.data?.value) {
          // Try to extract project data
          try {
            const value = dataResult.data.value;
            this._processLevelDBEntry(key, value);
            foundProjects = true;
          } catch (err) {
            console.warn(`Error processing LevelDB entry for key ${key}:`, err);
          }
        }
      }
      
      // If we couldn't find any projects, fall back to samples
      if (!foundProjects) {
        console.warn('Could not extract any project data from LevelDB');
        this._createSampleProjects();
      } else {
        console.log(`Successfully extracted ${this.cachedProjects.size} projects from Claude Desktop`);
      }
    } catch (error) {
      console.error('Error reading projects from LevelDB:', error);
      // Fall back to sample projects
      this._createSampleProjects();
    }
  }
  
  /**
   * Process a LevelDB entry and extract project data
   */
  private _processLevelDBEntry(key: string, value: any): void {
    try {
      // Handle different data formats
      if (typeof value === 'string' && value.startsWith('{')) {
        // Try to parse JSON string
        try {
          const data = JSON.parse(value);
          this._extractProjectData(data, key);
        } catch (e) {
          console.warn(`Could not parse JSON in key ${key}`);
        }
      } else if (typeof value === 'object') {
        // Process object directly
        this._extractProjectData(value, key);
      }
    } catch (error) {
      console.warn(`Error processing LevelDB entry ${key}:`, error);
    }
  }
  
  /**
   * Extract project data from a LevelDB value
   */
  private _extractProjectData(data: any, sourceKey: string): void {
    if (!data) return;
    
    // Look for project data structures
    if (data.id && (data.name || data.title)) {
      // Looks like a direct project object
      this._addProject(data);
      return;
    }
    
    // Check if data contains a projects array or object
    if (data.projects) {
      if (Array.isArray(data.projects)) {
        for (const project of data.projects) {
          this._addProject(project);
        }
      } else if (typeof data.projects === 'object') {
        for (const id in data.projects) {
          const project = data.projects[id];
          if (project && typeof project === 'object') {
            this._addProject({ ...project, id });
          }
        }
      }
      return;
    }
    
    // Check if data contains a project list
    if (data.projectList || data.project_list) {
      const projectList = data.projectList || data.project_list;
      if (Array.isArray(projectList)) {
        for (const project of projectList) {
          this._addProject(project);
        }
      } else if (typeof projectList === 'object') {
        for (const id in projectList) {
          this._addProject({ ...projectList[id], id });
        }
      }
      return;
    }
    
    // Check for any objects that might represent projects
    if (typeof data === 'object') {
      for (const key in data) {
        const value = data[key];
        if (value && typeof value === 'object') {
          // If it has id, name/title, and other project-like properties
          if (value.id && (value.name || value.title)) {
            this._addProject(value);
          }
          
          // Also check arrays
          if (Array.isArray(value)) {
            for (const item of value) {
              if (item && typeof item === 'object' && item.id && (item.name || item.title)) {
                this._addProject(item);
              }
            }
          }
        }
      }
    }
  }
  
  /**
   * Add a project to the cache
   */
  private _addProject(data: any): void {
    if (!data || !data.id) return;
    
    const now = new Date().toISOString();
    
    // Format the project according to our interface
    const project = {
      id: data.id,
      name: data.name || data.title || `Project ${data.id.substring(0, 8)}`,
      description: data.description || '',
      createdAt: data.createdAt || data.created_at || now,
      updatedAt: data.updatedAt || data.updated_at || now,
      ownerId: data.ownerId || data.owner_id || 'local-user',
      isShared: Boolean(data.isShared || data.is_shared),
      knowledgeBase: {
        id: data.knowledgeBaseId || data.knowledge_base_id || `kb-${crypto.randomBytes(4).toString('hex')}`,
        fileCount: data.fileCount || data.file_count || 0,
        totalSizeBytes: data.totalSizeBytes || data.total_size_bytes || 0,
        lastUpdated: data.lastUpdated || data.last_updated || now
      }
    };
    
    // Check if we already have this project
    if (!this.cachedProjects.has(project.id)) {
      this.cachedProjects.set(project.id, project);
      this.cachedFiles.set(project.id, new Map());
      
      console.log(`Added project: ${project.name} (${project.id})`);
    }
  }
  
  /**
   * Create sample projects (fallback when LevelDB access fails)
   */
  private _createSampleProjects(): void {
    console.log('Creating sample projects (fallback)');
    super.createSampleProjects();
  }
}