import { ClaudeAPIClient } from './interfaces.js';
import { MockClaudeClient } from './mock-claude-client.js';
import { ClaudeDesktopClient } from './claude-desktop-client.js';
import { ClaudeBrowserClient } from './claude-browser-client.js';
import { LevelDBDesktopClient } from './mcp-leveldb-client.js';
import { getApiKey } from '../config/configure.js';
import * as fsPromises from 'node:fs/promises';
import * as fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';

// Function to determine API mode from config or environment
function getApiMode(): string {
  // First check environment variable
  if (process.env.CLAUDE_SYNC_API_MODE) {
    return process.env.CLAUDE_SYNC_API_MODE;
  }
  
  // Then check config file
  try {
    const configPath = path.join(os.homedir(), '.claude-sync-config');
    if (fs.existsSync(configPath)) {
      const configContent = fs.readFileSync(configPath, 'utf-8');
      const config = JSON.parse(configContent);
      
      // Set LevelDB port from config if available
      if (config.mcpLeveldbPort && !process.env.MCP_LEVELDB_PORT) {
        process.env.MCP_LEVELDB_PORT = config.mcpLeveldbPort.toString();
      }
      
      if (config.apiMode) {
        return config.apiMode;
      }
    }
  } catch (error) {
    console.warn('Error reading config file:', error);
  }
  
  // Default to desktop mode
  return 'desktop';
}

// API mode options: 'desktop', 'browser', 'real', 'mock', 'leveldb'
const API_MODE = getApiMode();

/**
 * Factory for creating Claude API clients
 */
export class ClaudeClientFactory {
  private static desktopClient: ClaudeDesktopClient | null = null;
  private static mockClient: MockClaudeClient | null = null;
  private static browserClient: ClaudeBrowserClient | null = null;
  private static leveldbClient: LevelDBDesktopClient | null = null;
  
  /**
   * Get a Claude API client based on current configuration
   */
  static getClient(): ClaudeAPIClient {
    switch (API_MODE) {
      case 'desktop':
        return this.getDesktopClient();
      
      case 'browser':
        return this.getBrowserClient();
      
      case 'leveldb':
        return this.getLevelDBClient();
      
      case 'real':
        // Eventually implement web API client here
        console.warn('Web API client not yet implemented. Using desktop client instead.');
        return this.getDesktopClient();
      
      case 'mock':
      default:
        return this.getMockClient();
    }
  }
  
  /**
   * Get the Claude Desktop client (singleton)
   */
  static getDesktopClient(): ClaudeAPIClient {
    if (!this.desktopClient) {
      this.desktopClient = new ClaudeDesktopClient();
    }
    return this.desktopClient;
  }
  
  /**
   * Get a mock client (singleton for consistency)
   */
  static getMockClient(): ClaudeAPIClient {
    if (!this.mockClient) {
      this.mockClient = new MockClaudeClient();
    }
    return this.mockClient;
  }
  
  /**
   * Get the browser automation client (singleton)
   */
  static getBrowserClient(): ClaudeAPIClient {
    if (!this.browserClient) {
      // Initialize with credentials if available
      const email = process.env.CLAUDE_EMAIL;
      const password = process.env.CLAUDE_PASSWORD;
      
      if (email && password) {
        this.browserClient = new ClaudeBrowserClient({ email, password });
      } else {
        this.browserClient = new ClaudeBrowserClient();
        console.warn('No Claude.ai credentials found in environment. Browser automation will require manual login.');
      }
    }
    return this.browserClient;
  }
  
  /**
   * Get the LevelDB-enabled Desktop client (singleton)
   * This client uses the MCP to access Claude Desktop's LevelDB database
   */
  static getLevelDBClient(): ClaudeAPIClient {
    if (!this.leveldbClient) {
      // Use port 3000 by default for the MCP server
      const mcpPort = process.env.MCP_LEVELDB_PORT ? 
        parseInt(process.env.MCP_LEVELDB_PORT, 10) : 3000;
      
      this.leveldbClient = new LevelDBDesktopClient(mcpPort);
      console.log(`Using LevelDB MCP on port ${mcpPort}`);
    }
    return this.leveldbClient;
  }

  /**
   * Check if Claude Desktop is installed
   */
  static async isClaudeDesktopInstalled(): Promise<boolean> {
    try {
      let appDataPath = '';
      
      // Determine Claude Desktop storage location based on OS
      if (os.platform() === 'darwin') {
        appDataPath = path.join(os.homedir(), 'Library', 'Application Support', 'Claude');
      } else if (os.platform() === 'win32') {
        appDataPath = path.join(os.homedir(), 'AppData', 'Roaming', 'Claude');
      } else {
        appDataPath = path.join(os.homedir(), '.config', 'Claude');
      }
      
      // Check if the directory exists
      await fsPromises.access(appDataPath);
      return true;
    } catch (error) {
      return false;
    }
  }
}