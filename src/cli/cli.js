/**
 * Claude Sync CLI
 * This is a placeholder file for testing purposes
 */

import { Command } from 'commander';
import * as configManager from '../config/config-manager.js';

// Create a CLI command instance
const program = new Command();

// Configure the CLI
program
  .name('claude-sync')
  .description('CLI tool for synchronizing between Claude Code and Claude AI projects')
  .version('0.1.0');

// Add commands
function addCommands() {
  // Sync command
  program
    .command('sync')
    .description('Synchronize local files with Claude AI projects')
    .option('-p, --project <projectId>', 'Project ID to sync with')
    .option('-d, --dir <directory>', 'Local directory to sync')
    .option('-w, --watch', 'Watch for changes and sync automatically')
    .action((options) => {
      console.log('Sync command executed with options:', options);
    });
  
  // Server command
  program
    .command('server')
    .description('Start Claude Sync MCP server')
    .option('-p, --port <port>', 'Port to listen on', '3000')
    .action((options) => {
      console.log('Server command executed with options:', options);
    });
  
  // Config command
  program
    .command('config')
    .description('Configure Claude Sync')
    .option('-s, --set <key=value...>', 'Set configuration values')
    .option('-g, --get <key>', 'Get configuration value')
    .option('-l, --list', 'List all configuration values')
    .action((options) => {
      console.log('Config command executed with options:', options);
    });
}

// Add the commands to the program
addCommands();

// Helper method to load configuration
function loadConfig() {
  return configManager.loadConfig();
}

// Export the CLI methods for testing
export default {
  program,
  loadConfig,
  getSyncCommand: () => program.commands.find(cmd => cmd.name() === 'sync'),
  getServerCommand: () => program.commands.find(cmd => cmd.name() === 'server'),
  getConfigCommand: () => program.commands.find(cmd => cmd.name() === 'config'),
};