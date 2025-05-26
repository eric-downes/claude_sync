import http from 'node:http';
import { getAllProjects, getProjectConfig } from '../config/configure.js';
import { syncFiles } from '../sync/sync.js';
import { syncAllProjects } from '../sync/sync-all.js';
import { listAllProjects } from '../api/claude.js';
import path from 'node:path';
import os from 'node:os';

// Interface for MCP requests
interface MCPRequest {
  action: string;
  parameters?: Record<string, any>;
}

// Interface for MCP responses
interface MCPResponse {
  status: 'success' | 'error';
  data?: any;
  error?: string;
}

// Start the MCP server
export async function startMCPServer(port: number = 8022): Promise<void> {
  const server = http.createServer(handleRequest);
  
  server.listen(port, () => {
    console.log(`MCP server running at http://localhost:${port}/`);
    console.log(`To configure in Claude Code:`);
    console.log(`  claude mcp add claude-sync -- node dist/cli.js server --port ${port}`);
  });
}

// Handle incoming requests
async function handleRequest(req: http.IncomingMessage, res: http.ServerResponse): Promise<void> {
  // Set CORS headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  
  // Handle OPTIONS request (CORS preflight)
  if (req.method === 'OPTIONS') {
    res.writeHead(204);
    res.end();
    return;
  }
  
  // Handle POST request (MCP commands)
  if (req.method === 'POST' && req.url === '/') {
    let body = '';
    
    req.on('data', (chunk) => {
      body += chunk.toString();
    });
    
    req.on('end', async () => {
      try {
        const request: MCPRequest = JSON.parse(body);
        const response = await processRequest(request);
        
        res.setHeader('Content-Type', 'application/json');
        res.writeHead(200);
        res.end(JSON.stringify(response));
      } catch (error) {
        console.error('Error processing request:', error);
        
        res.setHeader('Content-Type', 'application/json');
        res.writeHead(500);
        res.end(JSON.stringify({
          status: 'error',
          error: 'Internal server error'
        }));
      }
    });
    
    return;
  }
  
  // Handle GET request (health check)
  if (req.method === 'GET' && req.url === '/') {
    res.setHeader('Content-Type', 'application/json');
    res.writeHead(200);
    res.end(JSON.stringify({
      status: 'success',
      data: {
        message: 'Claude Sync MCP server is running',
        version: '0.1.0'
      }
    }));
    return;
  }
  
  // Handle unknown requests
  res.writeHead(404);
  res.end('Not found');
}

// Process MCP requests
async function processRequest(request: MCPRequest): Promise<MCPResponse> {
  console.log('Received MCP request:', request);
  
  switch (request.action) {
    case 'list-projects':
      return await listProjects();
    
    case 'list-claude-projects':
      return await listClaudeProjects();
    
    case 'get-project':
      if (!request.parameters?.projectName) {
        return { 
          status: 'error', 
          error: 'Missing project name parameter' 
        };
      }
      return await getProject(request.parameters.projectName);
    
    case 'sync-project':
      if (!request.parameters?.projectName) {
        return { 
          status: 'error', 
          error: 'Missing project name parameter' 
        };
      }
      const direction = request.parameters.direction || 'both';
      return await syncProject(request.parameters.projectName, direction);
    
    case 'sync-all-projects':
      const baseDir = request.parameters?.baseDir || path.join(os.homedir(), 'claude');
      const syncDirection = request.parameters?.direction || 'both';
      const forceConfig = request.parameters?.forceConfig || false;
      return await syncAllProjectsAction(baseDir, syncDirection, forceConfig);
    
    default:
      return {
        status: 'error',
        error: `Unknown action: ${request.action}`
      };
  }
}

// List all configured projects
async function listProjects(): Promise<MCPResponse> {
  try {
    const projects = getAllProjects();
    return {
      status: 'success',
      data: {
        projects: Object.keys(projects).map(name => ({
          name,
          id: projects[name].projectId,
          localPath: projects[name].localPath,
          lastSynced: projects[name].lastSynced
        }))
      }
    };
  } catch (error) {
    console.error('Error listing projects:', error);
    return {
      status: 'error',
      error: 'Failed to list projects'
    };
  }
}

// Get project details
async function getProject(projectName: string): Promise<MCPResponse> {
  try {
    const project = getProjectConfig(projectName);
    
    if (!project) {
      return {
        status: 'error',
        error: `Project "${projectName}" not found`
      };
    }
    
    return {
      status: 'success',
      data: {
        name: projectName,
        id: project.projectId,
        localPath: project.localPath,
        lastSynced: project.lastSynced,
        excludePatterns: project.excludePatterns
      }
    };
  } catch (error) {
    console.error(`Error getting project ${projectName}:`, error);
    return {
      status: 'error',
      error: `Failed to get project "${projectName}"`
    };
  }
}

// Sync a project
async function syncProject(projectName: string, direction: 'upload' | 'download' | 'both'): Promise<MCPResponse> {
  try {
    await syncFiles(projectName, direction);
    
    return {
      status: 'success',
      data: {
        message: `Project "${projectName}" synced successfully`,
        direction
      }
    };
  } catch (error) {
    console.error(`Error syncing project ${projectName}:`, error);
    return {
      status: 'error',
      error: `Failed to sync project "${projectName}": ${error}`
    };
  }
}

// List all Claude.ai projects
async function listClaudeProjects(): Promise<MCPResponse> {
  try {
    const projects = await listAllProjects();
    
    return {
      status: 'success',
      data: {
        projects: projects.map(project => ({
          id: project.id,
          name: project.name,
          description: project.description || '',
          createdAt: project.createdAt,
          updatedAt: project.updatedAt
        }))
      }
    };
  } catch (error) {
    console.error('Error listing Claude.ai projects:', error);
    return {
      status: 'error',
      error: 'Failed to list Claude.ai projects'
    };
  }
}

// Sync all projects
async function syncAllProjectsAction(
  baseDir: string, 
  direction: 'upload' | 'download' | 'both',
  forceConfig: boolean
): Promise<MCPResponse> {
  try {
    await syncAllProjects({
      baseDir,
      direction,
      forceConfig
    });
    
    return {
      status: 'success',
      data: {
        message: 'All projects synced successfully',
        baseDir,
        direction
      }
    };
  } catch (error) {
    console.error('Error syncing all projects:', error);
    return {
      status: 'error',
      error: `Failed to sync all projects: ${error}`
    };
  }
}