#!/usr/bin/env node

/**
 * Test script for the LevelDB MCP integration with Claude Sync
 * 
 * This script sets the API mode to leveldb and then lists all projects
 * detected from Claude Desktop's LevelDB database.
 * 
 * Usage:
 * node scripts/test-leveldb-mode.js [port]
 * 
 * Where [port] is the optional port number where the LevelDB MCP server is running
 * (defaults to 3000).
 */

import { exec } from 'child_process';
import { promisify } from 'util';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs';
import os from 'os';

const execAsync = promisify(exec);
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, '..');

// Get port from command line args or use default
const port = process.argv[2] || '3000';

async function main() {
  console.log('Testing Claude Sync with LevelDB MCP integration');
  console.log(`Using MCP port: ${port}`);
  
  // Save current API mode
  let originalMode = 'desktop';
  try {
    const configPath = path.join(os.homedir(), '.claude-sync-config');
    if (fs.existsSync(configPath)) {
      const configContent = fs.readFileSync(configPath, 'utf-8');
      const config = JSON.parse(configContent);
      originalMode = config.apiMode || 'desktop';
    }
  } catch (error) {
    // Ignore - will use default mode
  }
  
  try {
    // Set API mode to leveldb
    console.log('\n1. Setting API mode to leveldb...');
    await execAsync(`cd ${projectRoot} && node dist/cli.js mode -m leveldb -p ${port}`);
    
    // List projects
    console.log('\n2. Listing projects from Claude Desktop LevelDB...');
    const { stdout, stderr } = await execAsync(`cd ${projectRoot} && node dist/cli.js list-projects`);
    
    if (stderr) {
      console.error('Error listing projects:', stderr);
    } else {
      console.log(stdout);
    }
  } catch (error) {
    console.error('Error:', error.message);
    
    if (error.stderr) {
      console.error('stderr:', error.stderr);
    }
  } finally {
    // Restore original API mode
    try {
      console.log(`\nRestoring original API mode: ${originalMode}...`);
      await execAsync(`cd ${projectRoot} && node dist/cli.js mode -m ${originalMode}`);
      console.log('Done!');
    } catch (restoreError) {
      console.error('Error restoring original API mode:', restoreError.message);
    }
  }
}

main().catch(console.error);