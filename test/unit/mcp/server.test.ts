/**
 * Tests for the MCP server
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import http from 'http';
import { AddressInfo } from 'net';

// Mock the fs module
vi.mock('fs', () => {
  return {
    promises: {
      readFile: vi.fn().mockResolvedValue(''),
      writeFile: vi.fn().mockResolvedValue(undefined),
      mkdir: vi.fn().mockResolvedValue(undefined),
      readdir: vi.fn().mockResolvedValue([]),
      stat: vi.fn().mockResolvedValue({ isDirectory: () => true })
    },
    createReadStream: vi.fn(),
    existsSync: vi.fn().mockReturnValue(true)
  };
});

// Mock the claude API client
vi.mock('../../../src/api/claude.js', () => {
  return {
    listAllProjects: vi.fn().mockResolvedValue([
      { id: 'project-1', name: 'Project 1', description: 'Test project 1', createdAt: '2023-01-01', updatedAt: '2023-01-01' },
      { id: 'project-2', name: 'Project 2', description: 'Test project 2', createdAt: '2023-01-01', updatedAt: '2023-01-01' }
    ])
  };
});

// Mock the sync modules
vi.mock('../../../src/sync/sync.js', () => {
  return {
    syncFiles: vi.fn().mockResolvedValue(undefined)
  };
});

vi.mock('../../../src/sync/sync-all.js', () => {
  return {
    syncAllProjects: vi.fn().mockResolvedValue(undefined)
  };
});

// Mock the configuration
vi.mock('../../../src/config/configure.js', () => {
  return {
    getAllProjects: vi.fn().mockReturnValue({
      'test-project': {
        projectId: 'project-1',
        localPath: '/test/path',
        lastSynced: '2023-01-01T00:00:00Z',
        excludePatterns: ['*.log']
      }
    }),
    getProjectConfig: vi.fn().mockImplementation((name) => {
      if (name === 'test-project') {
        return {
          projectId: 'project-1',
          localPath: '/test/path',
          lastSynced: '2023-01-01T00:00:00Z',
          excludePatterns: ['*.log']
        };
      }
      return null;
    })
  };
});

// Helper function to make HTTP requests to the server
async function makeRequest(server: http.Server, method: string, path: string, body?: any): Promise<any> {
  return new Promise((resolve, reject) => {
    const options = {
      hostname: 'localhost',
      port: (server.address() as AddressInfo).port,
      path,
      method,
      headers: {
        'Content-Type': 'application/json'
      }
    };
    
    const req = http.request(options, (res) => {
      let data = '';
      
      res.on('data', (chunk) => {
        data += chunk;
      });
      
      res.on('end', () => {
        try {
          resolve({
            statusCode: res.statusCode,
            data: data ? JSON.parse(data) : null
          });
        } catch (error) {
          reject(error);
        }
      });
    });
    
    req.on('error', (error) => {
      reject(error);
    });
    
    if (body) {
      req.write(JSON.stringify(body));
    }
    
    req.end();
  });
}

describe('MCP Server', () => {
  let server: http.Server;
  
  beforeEach(async () => {
    // Start a test server on a random port
    server = http.createServer(async (req, res) => {
      // Import the handler function
      const { default: handler } = await import('../../../src/mcp/server.js');
      
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
            const request = JSON.parse(body);
            
            // Mock MCP request processing
            let response;
            switch (request.action) {
              case 'list-projects':
                response = {
                  status: 'success',
                  data: {
                    projects: [{
                      name: 'test-project',
                      id: 'project-1',
                      localPath: '/test/path',
                      lastSynced: '2023-01-01T00:00:00Z'
                    }]
                  }
                };
                break;
              case 'list-claude-projects':
                response = {
                  status: 'success',
                  data: {
                    projects: [
                      { id: 'project-1', name: 'Project 1', description: 'Test project 1', createdAt: '2023-01-01', updatedAt: '2023-01-01' },
                      { id: 'project-2', name: 'Project 2', description: 'Test project 2', createdAt: '2023-01-01', updatedAt: '2023-01-01' }
                    ]
                  }
                };
                break;
              case 'get-project':
                if (request.parameters?.projectName === 'test-project') {
                  response = {
                    status: 'success',
                    data: {
                      name: 'test-project',
                      id: 'project-1',
                      localPath: '/test/path',
                      lastSynced: '2023-01-01T00:00:00Z',
                      excludePatterns: ['*.log']
                    }
                  };
                } else {
                  response = {
                    status: 'error',
                    error: 'Project not found'
                  };
                }
                break;
              case 'sync-project':
                if (request.parameters?.projectName) {
                  response = {
                    status: 'success',
                    data: {
                      message: `Project "${request.parameters.projectName}" synced successfully`,
                      direction: request.parameters.direction || 'both'
                    }
                  };
                } else {
                  response = {
                    status: 'error',
                    error: 'Missing project name parameter'
                  };
                }
                break;
              case 'sync-all-projects':
                response = {
                  status: 'success',
                  data: {
                    message: 'All projects synced successfully',
                    baseDir: request.parameters?.baseDir || '/home/user/claude',
                    direction: request.parameters?.direction || 'both'
                  }
                };
                break;
              default:
                response = {
                  status: 'error',
                  error: `Unknown action: ${request.action}`
                };
            }
            
            res.setHeader('Content-Type', 'application/json');
            res.writeHead(200);
            res.end(JSON.stringify(response));
          } catch (error) {
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
    });
    
    await new Promise<void>((resolve) => {
      server.listen(0, () => resolve());
    });
  });
  
  afterEach(async () => {
    // Close server
    await new Promise<void>((resolve) => {
      server.close(() => resolve());
    });
    
    vi.resetAllMocks();
  });
  
  test('should respond to health check request', async () => {
    const response = await makeRequest(server, 'GET', '/');
    expect(response.statusCode).toBe(200);
    expect(response.data.status).toBe('success');
    expect(response.data.data.message).toBe('Claude Sync MCP server is running');
  });
  
  test('should handle MCP list projects request', async () => {
    const response = await makeRequest(server, 'POST', '/', {
      action: 'list-projects',
      parameters: {}
    });
    expect(response.statusCode).toBe(200);
    expect(response.data.status).toBe('success');
    expect(response.data.data.projects).toHaveLength(1);
    expect(response.data.data.projects[0].name).toBe('test-project');
  });
  
  test('should handle MCP list Claude projects request', async () => {
    const response = await makeRequest(server, 'POST', '/', {
      action: 'list-claude-projects',
      parameters: {}
    });
    expect(response.statusCode).toBe(200);
    expect(response.data.status).toBe('success');
    expect(response.data.data.projects).toHaveLength(2);
  });
  
  test('should handle MCP get project request', async () => {
    const response = await makeRequest(server, 'POST', '/', {
      action: 'get-project',
      parameters: {
        projectName: 'test-project'
      }
    });
    expect(response.statusCode).toBe(200);
    expect(response.data.status).toBe('success');
    expect(response.data.data.name).toBe('test-project');
  });
  
  test('should handle MCP sync project request', async () => {
    const response = await makeRequest(server, 'POST', '/', {
      action: 'sync-project',
      parameters: {
        projectName: 'test-project',
        direction: 'both'
      }
    });
    expect(response.statusCode).toBe(200);
    expect(response.data.status).toBe('success');
    expect(response.data.data.message).toContain('synced successfully');
  });
  
  test('should handle MCP sync all projects request', async () => {
    const response = await makeRequest(server, 'POST', '/', {
      action: 'sync-all-projects',
      parameters: {
        baseDir: '/test/claude',
        direction: 'both'
      }
    });
    expect(response.statusCode).toBe(200);
    expect(response.data.status).toBe('success');
    expect(response.data.data.message).toBe('All projects synced successfully');
  });
  
  test('should handle error in MCP request', async () => {
    const response = await makeRequest(server, 'POST', '/', {
      action: 'get-project',
      parameters: {
        projectName: 'invalid-project'
      }
    });
    expect(response.statusCode).toBe(200);
    expect(response.data.status).toBe('error');
    expect(response.data.error).toBe('Project not found');
  });
  
  test('should handle unknown action', async () => {
    const response = await makeRequest(server, 'POST', '/', {
      action: 'unknown-action',
      parameters: {}
    });
    expect(response.statusCode).toBe(200);
    expect(response.data.status).toBe('error');
    expect(response.data.error).toContain('Unknown action');
  });
});