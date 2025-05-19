#!/usr/bin/env node

import { Command } from 'commander';
import dotenv from 'dotenv';
import { configureProject } from './config/configure.js';
import { syncFiles } from './sync/sync.js';
import { syncAllProjects } from './sync/sync-all.js';
import { watchProject } from './sync/watcher.js';
import { startMCPServer } from './mcp/server.js';
import { listAllProjects } from './api/claude.js';
import path from 'node:path';
import os from 'node:os';
import * as fs from 'node:fs/promises';

// Load environment variables
dotenv.config();

const program = new Command();

program
  .name('claude-sync')
  .description('Tool for synchronizing between Claude Code and Claude AI projects')
  .version('0.1.0');

program
  .command('config')
  .description('Configure a new Claude AI project for synchronization')
  .action(async () => {
    await configureProject();
  });

program
  .command('sync')
  .description('Synchronize files with a Claude AI project')
  .option('-p, --project <name>', 'Project name to sync with')
  .option('-d, --direction <direction>', 'Sync direction: upload, download, or both', 'both')
  .action(async (options) => {
    await syncFiles(options.project, options.direction);
  });

program
  .command('watch')
  .description('Watch files for changes and automatically sync to a Claude AI project')
  .requiredOption('-p, --project <name>', 'Project name to sync with')
  .action(async (options) => {
    try {
      const stopWatching = await watchProject(options.project);
      
      // Handle termination signals
      process.on('SIGINT', () => {
        stopWatching();
        process.exit(0);
      });
      
      process.on('SIGTERM', () => {
        stopWatching();
        process.exit(0);
      });
      
      console.log('Watching for file changes. Press Ctrl+C to stop.');
    } catch (error) {
      console.error('Error starting watch mode:', error);
      process.exit(1);
    }
  });

program
  .command('mode')
  .description('Set the API mode for Claude Sync')
  .option('-m, --mode <mode>', 'API mode: desktop, browser, leveldb, or mock', 'desktop')
  .option('-p, --port <port>', 'Port for LevelDB MCP server (only for leveldb mode)', '3000')
  .action(async (options) => {
    // Set the API mode in environment
    process.env.CLAUDE_SYNC_API_MODE = options.mode;
    
    // Save to config file for persistence
    const configPath = path.join(os.homedir(), '.claude-sync-config');
    const config = { apiMode: options.mode };
    
    // Add port for leveldb mode
    if (options.mode === 'leveldb') {
      process.env.MCP_LEVELDB_PORT = options.port;
      config.mcpLeveldbPort = options.port;
    }
    
    await fs.writeFile(configPath, JSON.stringify(config), 'utf-8');
    
    console.log(`Claude Sync API mode set to: ${options.mode}`);
    
    // Show additional instructions for different modes
    if (options.mode === 'browser') {
      console.log('\nNOTE: Browser mode requires Claude.ai credentials.');
      console.log('Set these environment variables or add them to .env:');
      console.log('  CLAUDE_EMAIL=your-email@example.com');
      console.log('  CLAUDE_PASSWORD=your-password');
    } else if (options.mode === 'leveldb') {
      console.log(`\nNOTE: LevelDB mode requires the MCP server to be running on port ${options.port}.`);
      console.log('Start the LevelDB MCP server with:');
      console.log(`  cd mcp-leveldb && npm run build && node dist/cli.js server -p ${options.port}`);
      console.log('\nRegister the MCP with Claude Code:');
      console.log(`  claude mcp add leveldb -- node /Users/eric/compute/claude_sync/mcp-leveldb/dist/cli.js server -p ${options.port}`);
    }
  });

program
  .command('list-projects')
  .alias('list')
  .description('List all projects in your Claude.ai account')
  .option('-o, --output <format>', 'Output format: json or table', 'table')
  .action(async (options) => {
    try {
      const projects = await listAllProjects();
      
      if (options.output === 'json') {
        console.log(JSON.stringify(projects, null, 2));
      } else {
        console.log('\nClaude AI Projects:\n');
        console.log('ID                                  | Name                 | Description');
        console.log('------------------------------------ | -------------------- | --------------------');
        
        projects.forEach(project => {
          const id = project.id.padEnd(36);
          const name = (project.name || '').padEnd(20);
          const description = project.description || '';
          console.log(`${id} | ${name} | ${description}`);
        });
        
        console.log('\nTotal projects:', projects.length);
      }
    } catch (error) {
      console.error('Error listing projects:', error);
      process.exit(1);
    }
  });

program
  .command('sync-all')
  .description('Sync all Claude.ai projects to subdirectories')
  .option('-d, --dir <path>', 'Base directory for project subdirectories', path.join(os.homedir(), 'claude'))
  .option('-m, --mode <mode>', 'Sync mode: download, upload, or both', 'both')
  .option('-f, --force-config', 'Force reconfiguration of all projects', false)
  .action(async (options) => {
    try {
      await syncAllProjects({
        baseDir: options.dir,
        direction: options.mode,
        forceConfig: options.forceConfig
      });
    } catch (error) {
      console.error('Error syncing all projects:', error);
      process.exit(1);
    }
  });

program
  .command('server')
  .description('Start the MCP server for Claude Code integration')
  .option('-p, --port <number>', 'Port to run the server on', '8022')
  .action(async (options) => {
    await startMCPServer(parseInt(options.port));
  });

program.parse();