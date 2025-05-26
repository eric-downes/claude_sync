import fs from 'fs/promises';
import path from 'path';
import os from 'os';
import { 
  SyncStateDatabase, 
  BackupEntry, 
  generateBackupId, 
  calculateFileHash 
} from './sync-state.js';

export interface BackupOptions {
  enabled: boolean;
  retentionCount: number;    // Keep N backups per file (default: 5)
  compressionLevel: number;  // 0-9 for compression (not implemented yet)
  location: 'local' | 'remote' | 'both';
  autoCleanup: boolean;      // Automatically clean up old backups
}

export interface BackupResult {
  success: boolean;
  backupId?: string;
  backupPath?: string;
  error?: string;
}

export class BackupManager {
  private database: SyncStateDatabase;
  private projectId: string;
  private options: BackupOptions;
  private backupBaseDir: string;
  
  constructor(
    database: SyncStateDatabase, 
    projectId: string, 
    options: Partial<BackupOptions> = {}
  ) {
    this.database = database;
    this.projectId = projectId;
    this.options = {
      enabled: true,
      retentionCount: 5,
      compressionLevel: 0,
      location: 'local',
      autoCleanup: true,
      ...options
    };
    
    this.backupBaseDir = path.join(os.homedir(), '.claude-sync', 'backups', projectId);
  }
  
  /**
   * Create a backup of a file before modifying it
   */
  async createBackup(
    originalPath: string, 
    reason: string = 'sync'
  ): Promise<BackupResult> {
    if (!this.options.enabled) {
      return { success: true }; // Backups disabled, consider it successful
    }
    
    try {
      // Check if file exists
      const stats = await fs.stat(originalPath);
      if (!stats.isFile()) {
        return { success: false, error: 'Path is not a file' };
      }
      
      // Ensure backup directory exists
      await fs.mkdir(this.backupBaseDir, { recursive: true });
      
      // Generate backup info
      const backupId = generateBackupId();
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
      const fileName = path.basename(originalPath);
      const backupFileName = `${fileName}.${timestamp}.${backupId.substring(0, 8)}.bak`;
      const backupPath = path.join(this.backupBaseDir, backupFileName);
      
      // Calculate file hash
      const fileHash = await calculateFileHash(originalPath);
      
      // Copy file to backup location
      await fs.copyFile(originalPath, backupPath);
      
      // Verify backup integrity
      const backupHash = await calculateFileHash(backupPath);
      if (fileHash !== backupHash) {
        // Cleanup failed backup
        await fs.unlink(backupPath).catch(() => {});
        return { success: false, error: 'Backup integrity verification failed' };
      }
      
      // Create backup entry in database
      const backupEntry: BackupEntry = {
        backupId,
        originalPath: path.relative(process.cwd(), originalPath),
        backupPath,
        createdAt: new Date(),
        fileHash,
        projectId: this.projectId,
        reason
      };
      
      await this.database.createBackup(backupEntry);
      
      // Auto-cleanup if enabled
      if (this.options.autoCleanup) {
        await this.database.cleanupOldBackups(this.projectId, this.options.retentionCount);
      }
      
      return {
        success: true,
        backupId,
        backupPath
      };
      
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error'
      };
    }
  }
  
  /**
   * Restore a file from backup
   */
  async restoreFromBackup(
    backupId: string, 
    targetPath?: string
  ): Promise<BackupResult> {
    try {
      const backups = await this.database.listBackups(this.projectId);
      const backup = backups.find(b => b.backupId === backupId);
      
      if (!backup) {
        return { success: false, error: 'Backup not found' };
      }
      
      // Check if backup file exists
      try {
        await fs.access(backup.backupPath);
      } catch {
        return { success: false, error: 'Backup file no longer exists on disk' };
      }
      
      // Determine target path
      const restorePath = targetPath || backup.originalPath;
      
      // Ensure target directory exists
      await fs.mkdir(path.dirname(restorePath), { recursive: true });
      
      // Restore the file
      await fs.copyFile(backup.backupPath, restorePath);
      
      // Verify restoration integrity
      const restoredHash = await calculateFileHash(restorePath);
      if (restoredHash !== backup.fileHash) {
        return { success: false, error: 'Restored file integrity verification failed' };
      }
      
      return {
        success: true,
        backupId: backup.backupId,
        backupPath: restorePath
      };
      
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error'
      };
    }
  }
  
  /**
   * List available backups for a file or project
   */
  async listBackups(originalPath?: string): Promise<BackupEntry[]> {
    return await this.database.listBackups(this.projectId, originalPath);
  }
  
  /**
   * Delete a specific backup
   */
  async deleteBackup(backupId: string): Promise<BackupResult> {
    try {
      await this.database.deleteBackup(backupId);
      return { success: true };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error'
      };
    }
  }
  
  /**
   * Clean up old backups based on retention policy
   */
  async cleanupOldBackups(): Promise<{ deletedCount: number; errors: string[] }> {
    const errors: string[] = [];
    let deletedCount = 0;
    
    try {
      const backupsBefore = await this.database.listBackups(this.projectId);
      await this.database.cleanupOldBackups(this.projectId, this.options.retentionCount);
      const backupsAfter = await this.database.listBackups(this.projectId);
      
      deletedCount = backupsBefore.length - backupsAfter.length;
      
    } catch (error) {
      errors.push(error instanceof Error ? error.message : 'Unknown error');
    }
    
    return { deletedCount, errors };
  }
  
  /**
   * Get backup statistics for the project
   */
  async getBackupStats(): Promise<{
    totalBackups: number;
    totalSizeBytes: number;
    oldestBackup?: Date;
    newestBackup?: Date;
    backupsByFile: Map<string, number>;
  }> {
    const backups = await this.database.listBackups(this.projectId);
    const backupsByFile = new Map<string, number>();
    let totalSizeBytes = 0;
    let oldestBackup: Date | undefined;
    let newestBackup: Date | undefined;
    
    for (const backup of backups) {
      // Count backups by file
      const count = backupsByFile.get(backup.originalPath) || 0;
      backupsByFile.set(backup.originalPath, count + 1);
      
      // Calculate total size
      try {
        const stats = await fs.stat(backup.backupPath);
        totalSizeBytes += stats.size;
      } catch {
        // Backup file may not exist, skip
      }
      
      // Track date range
      if (!oldestBackup || backup.createdAt < oldestBackup) {
        oldestBackup = backup.createdAt;
      }
      if (!newestBackup || backup.createdAt > newestBackup) {
        newestBackup = backup.createdAt;
      }
    }
    
    return {
      totalBackups: backups.length,
      totalSizeBytes,
      oldestBackup,
      newestBackup,
      backupsByFile
    };
  }
  
  /**
   * Check if a file has changed since the last backup
   */
  async hasFileChangedSinceBackup(filePath: string): Promise<boolean> {
    try {
      const currentHash = await calculateFileHash(filePath);
      const backups = await this.listBackups(path.relative(process.cwd(), filePath));
      
      if (backups.length === 0) {
        return true; // No backups exist, consider it changed
      }
      
      // Check against the most recent backup
      const latestBackup = backups[0]; // Already sorted by date (newest first)
      return currentHash !== latestBackup.fileHash;
      
    } catch {
      return true; // Error reading file, consider it changed
    }
  }
  
  /**
   * Create a backup only if the file has changed
   */
  async createBackupIfChanged(
    originalPath: string, 
    reason: string = 'sync'
  ): Promise<BackupResult> {
    const hasChanged = await this.hasFileChangedSinceBackup(originalPath);
    
    if (!hasChanged) {
      return { success: true }; // No backup needed
    }
    
    return this.createBackup(originalPath, reason);
  }
}

/**
 * Check if a file exists
 */
export async function fileExists(filePath: string): Promise<boolean> {
  try {
    await fs.access(filePath);
    return true;
  } catch {
    return false;
  }
}