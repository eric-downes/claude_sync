#!/usr/bin/env node

import { Command } from 'commander';
import dotenv from 'dotenv';
import { configureProject, getProjectConfig } from './config/configure.js';
import { syncFiles } from './sync/sync.js';
import { SafeSync } from './sync/safe-sync.js';
import { syncAllProjects } from './sync/sync-all.js';
import { watchProject } from './sync/watcher.js';
import { startMCPServer } from './mcp/server.js';
import { listAllProjects } from './api/claude.js';
import { ClaudeClientFactory } from './api/client-factory.js';
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
  .option('--dry-run', 'Preview changes without executing them', false)
  .option('--no-backup', 'Disable automatic backups', false)
  .option('--backup-retention <count>', 'Number of backups to retain per file', '5')
  .option('--no-validation', 'Skip pre-sync validation', false)
  .option('--conflict <strategy>', 'Conflict resolution: ask, skip, local_wins, remote_wins, backup_and_merge', 'ask')
  .option('--force', 'Force sync even with validation warnings', false)
  .option('--verbose', 'Show detailed output', false)
  .option('--legacy', 'Use legacy sync implementation', false)
  .action(async (options) => {
    try {
      // Get project configuration
      const projectConfig = getProjectConfig(options.project);
      if (!projectConfig) {
        console.error(`Project "${options.project}" not found. Please configure it first using: claude-sync config`);
        process.exit(1);
      }

      if (options.legacy) {
        // Use legacy sync for backward compatibility
        await syncFiles(options.project, options.direction);
      } else {
        // Use new SafeSync implementation
        const client = ClaudeClientFactory.getClient();
        const safeSync = new SafeSync(client, projectConfig.projectId, projectConfig.localPath, {
          direction: options.direction,
          dryRun: options.dryRun,
          backup: {
            enabled: options.backup !== false,
            retentionCount: parseInt(options.backupRetention),
            compressionLevel: 0,
            location: 'local',
            autoCleanup: true
          },
          validation: {
            enabled: options.validation !== false,
            checkDiskSpace: true,
            checkPermissions: true,
            checkGitStatus: true,
            checkNetworkConnectivity: true,
            maxConflictCount: 10
          },
          conflictResolution: options.conflict,
          force: options.force,
          verbose: options.verbose,
          excludePatterns: projectConfig.excludePatterns || ['node_modules/**', '.git/**', '*.log', '.claude-sync/**']
        });

        const result = await safeSync.sync();

        // Display results
        if (options.verbose || options.dryRun) {
          console.log('\n' + '='.repeat(60));
          console.log('SYNC RESULTS');
          console.log('='.repeat(60));
          
          if (result.dryRun) {
            console.log('🏃 DRY RUN - No changes were made');
          }
          
          console.log(`📊 Operations: ${result.operations.length} planned, ${result.executedOperations.length} executed, ${result.skippedOperations.length} skipped`);
          console.log(`📁 Files: ${result.stats.filesUploaded} uploaded, ${result.stats.filesDownloaded} downloaded`);
          console.log(`📦 Backups: ${result.stats.backupsCreated} created`);
          console.log(`⚡ Conflicts: ${result.stats.conflictsResolved} resolved`);
          console.log(`⏱️  Duration: ${result.stats.duration}ms`);
          
          if (result.warnings.length > 0) {
            console.log('\n⚠️  WARNINGS:');
            result.warnings.forEach(warning => console.log(`  • ${warning}`));
          }
          
          if (result.errors.length > 0) {
            console.log('\n❌ ERRORS:');
            result.errors.forEach(error => console.log(`  • ${error}`));
          }
          
          if (result.validationResult?.recommendations.length > 0) {
            console.log('\n💡 RECOMMENDATIONS:');
            result.validationResult.recommendations.forEach(rec => console.log(`  • ${rec}`));
          }
        }

        if (!result.success) {
          console.error('\n❌ Sync failed. See errors above.');
          process.exit(1);
        } else if (options.dryRun) {
          console.log('\n✅ Dry run completed successfully. Use --no-dry-run to execute changes.');
        } else {
          console.log('\n✅ Sync completed successfully.');
        }
      }
    } catch (error) {
      console.error('Sync error:', error instanceof Error ? error.message : error);
      process.exit(1);
    }
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

// Backup management commands
const backupCmd = program
  .command('backup')
  .description('Manage sync backups');

backupCmd
  .command('list')
  .description('List available backups for a project')
  .option('-p, --project <name>', 'Project name')
  .option('-f, --file <path>', 'Show backups for specific file')
  .action(async (options) => {
    try {
      const projectConfig = getProjectConfig(options.project);
      if (!projectConfig) {
        console.error(`Project "${options.project}" not found.`);
        process.exit(1);
      }

      const { JsonSyncStateDatabase } = await import('./sync/sync-state.js');
      const { BackupManager } = await import('./sync/backup-manager.js');
      
      const database = new JsonSyncStateDatabase(projectConfig.projectId);
      const backupManager = new BackupManager(database, projectConfig.projectId);
      
      const backups = await backupManager.listBackups(options.file);
      
      if (backups.length === 0) {
        console.log('No backups found.');
        return;
      }
      
      console.log('\nBackups:\n');
      console.log('ID               | File                     | Created              | Reason');
      console.log('---------------- | ------------------------ | -------------------- | ----------');
      
      backups.forEach(backup => {
        const id = backup.backupId.substring(0, 16);
        const file = backup.originalPath.padEnd(24);
        const created = backup.createdAt.toISOString().replace('T', ' ').substring(0, 19);
        console.log(`${id} | ${file} | ${created} | ${backup.reason}`);
      });
      
      const stats = await backupManager.getBackupStats();
      console.log(`\nTotal: ${stats.totalBackups} backups, ${Math.round(stats.totalSizeBytes / 1024 / 1024)}MB`);
      
    } catch (error) {
      console.error('Error listing backups:', error instanceof Error ? error.message : error);
      process.exit(1);
    }
  });

backupCmd
  .command('restore')
  .description('Restore a file from backup')
  .requiredOption('-b, --backup-id <id>', 'Backup ID to restore')
  .option('-t, --target <path>', 'Target path (defaults to original location)')
  .action(async (options) => {
    try {
      // This would require project context - simplified for now
      console.log(`Restoring backup ${options.backupId}...`);
      console.log('Restore functionality requires project context. Use SafeSync.restoreFromBackup() directly.');
    } catch (error) {
      console.error('Error restoring backup:', error instanceof Error ? error.message : error);
      process.exit(1);
    }
  });

backupCmd
  .command('cleanup')
  .description('Clean up old backups')
  .option('-p, --project <name>', 'Project name')
  .option('-r, --retain <count>', 'Number of backups to retain per file', '5')
  .action(async (options) => {
    try {
      const projectConfig = getProjectConfig(options.project);
      if (!projectConfig) {
        console.error(`Project "${options.project}" not found.`);
        process.exit(1);
      }

      const { JsonSyncStateDatabase } = await import('./sync/sync-state.js');
      const { BackupManager } = await import('./sync/backup-manager.js');
      
      const database = new JsonSyncStateDatabase(projectConfig.projectId);
      const backupManager = new BackupManager(database, projectConfig.projectId);
      
      const result = await backupManager.cleanupOldBackups();
      
      console.log(`✅ Cleaned up ${result.deletedCount} old backups.`);
      
      if (result.errors.length > 0) {
        console.log('\n⚠️  Errors during cleanup:');
        result.errors.forEach(error => console.log(`  • ${error}`));
      }
      
    } catch (error) {
      console.error('Error cleaning up backups:', error instanceof Error ? error.message : error);
      process.exit(1);
    }
  });

// Status and diagnostics commands
program
  .command('status')
  .description('Show sync status and statistics')
  .option('-p, --project <name>', 'Project name')
  .action(async (options) => {
    try {
      const projectConfig = getProjectConfig(options.project);
      if (!projectConfig) {
        console.error(`Project "${options.project}" not found.`);
        process.exit(1);
      }

      const { JsonSyncStateDatabase } = await import('./sync/sync-state.js');
      const { BackupManager } = await import('./sync/backup-manager.js');
      
      const database = new JsonSyncStateDatabase(projectConfig.projectId);
      const backupManager = new BackupManager(database, projectConfig.projectId);
      
      await database.initialize();
      
      const fileStates = await database.listFileStates(projectConfig.projectId);
      const backupStats = await backupManager.getBackupStats();
      
      console.log('\n' + '='.repeat(50));
      console.log(`SYNC STATUS: ${options.project}`);
      console.log('='.repeat(50));
      console.log(`📁 Project ID: ${projectConfig.projectId}`);
      console.log(`📂 Local Path: ${projectConfig.localPath}`);
      console.log(`📊 Tracked Files: ${fileStates.length}`);
      console.log(`📦 Backups: ${backupStats.totalBackups} (${Math.round(backupStats.totalSizeBytes / 1024 / 1024)}MB)`);
      
      if (backupStats.oldestBackup && backupStats.newestBackup) {
        console.log(`📅 Backup Range: ${backupStats.oldestBackup.toDateString()} - ${backupStats.newestBackup.toDateString()}`);
      }
      
      const recentFiles = fileStates
        .sort((a, b) => b.lastSyncTime.getTime() - a.lastSyncTime.getTime())
        .slice(0, 5);
        
      if (recentFiles.length > 0) {
        console.log('\n📋 Recently Synced Files:');
        recentFiles.forEach(file => {
          const direction = file.syncDirection === 'upload' ? '⬆️' : file.syncDirection === 'download' ? '⬇️' : '↕️';
          const time = file.lastSyncTime.toISOString().replace('T', ' ').substring(0, 16);
          console.log(`  ${direction} ${file.localPath} (${time})`);
        });
      }
      
      await database.close();
      
    } catch (error) {
      console.error('Error getting status:', error instanceof Error ? error.message : error);
      process.exit(1);
    }
  });

program.parse();