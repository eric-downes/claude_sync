import fs from 'fs/promises';
import path from 'path';
import crypto from 'crypto';
import os from 'os';

export interface SyncStateEntry {
  fileId: string;           // Unique file identifier (hash of path)
  projectId: string;        // Project association
  localPath: string;        // Local file path (relative to project root)
  remoteId?: string;        // Remote file ID
  localHash: string;        // File content hash (SHA-256)
  remoteHash?: string;      // Remote content hash
  localMtime: Date;         // Last local modification time
  remoteMtime?: Date;       // Last remote modification time
  lastSyncTime: Date;       // Last successful sync
  syncDirection: 'upload' | 'download' | 'both';
  conflictState: 'none' | 'local_newer' | 'remote_newer' | 'both_modified';
  backupPath?: string;      // Path to backup copy
  size: number;             // File size in bytes
  isDeleted: boolean;       // Mark files as deleted instead of removing entries
}

export interface BackupEntry {
  backupId: string;         // Unique backup identifier
  originalPath: string;     // Original file path
  backupPath: string;       // Backup file path
  createdAt: Date;          // Backup creation time
  fileHash: string;         // File content hash at backup time
  projectId: string;        // Associated project
  reason: string;           // Reason for backup ('sync', 'conflict', 'manual')
}

export interface SyncStateDatabase {
  // File state management
  getFileState(projectId: string, localPath: string): Promise<SyncStateEntry | null>;
  saveFileState(entry: SyncStateEntry): Promise<void>;
  deleteFileState(projectId: string, localPath: string): Promise<void>;
  listFileStates(projectId: string): Promise<SyncStateEntry[]>;
  
  // Backup management
  createBackup(entry: BackupEntry): Promise<void>;
  listBackups(projectId: string, originalPath?: string): Promise<BackupEntry[]>;
  deleteBackup(backupId: string): Promise<void>;
  cleanupOldBackups(projectId: string, retentionCount: number): Promise<void>;
  
  // Database management
  initialize(): Promise<void>;
  close(): Promise<void>;
}

/**
 * Simple JSON-based sync state database
 * For production, this could be replaced with SQLite
 */
export class JsonSyncStateDatabase implements SyncStateDatabase {
  private dbPath: string;
  private syncStates: Map<string, SyncStateEntry> = new Map();
  private backups: Map<string, BackupEntry> = new Map();
  private initialized = false;
  
  constructor(projectId: string) {
    const dbDir = path.join(os.homedir(), '.claude-sync', 'state');
    this.dbPath = path.join(dbDir, `${projectId}.json`);
  }
  
  async initialize(): Promise<void> {
    if (this.initialized) return;
    
    // Ensure directory exists
    await fs.mkdir(path.dirname(this.dbPath), { recursive: true });
    
    // Load existing data
    try {
      const data = await fs.readFile(this.dbPath, 'utf-8');
      const parsed = JSON.parse(data);
      
      // Load sync states
      if (parsed.syncStates) {
        for (const entry of parsed.syncStates) {
          // Convert date strings back to Date objects
          entry.localMtime = new Date(entry.localMtime);
          entry.lastSyncTime = new Date(entry.lastSyncTime);
          if (entry.remoteMtime) entry.remoteMtime = new Date(entry.remoteMtime);
          
          this.syncStates.set(this.getStateKey(entry.projectId, entry.localPath), entry);
        }
      }
      
      // Load backups
      if (parsed.backups) {
        for (const backup of parsed.backups) {
          backup.createdAt = new Date(backup.createdAt);
          this.backups.set(backup.backupId, backup);
        }
      }
    } catch (error) {
      // File doesn't exist or is invalid, start fresh
      this.syncStates.clear();
      this.backups.clear();
    }
    
    this.initialized = true;
  }
  
  private async save(): Promise<void> {
    const data = {
      syncStates: Array.from(this.syncStates.values()),
      backups: Array.from(this.backups.values())
    };
    
    // Write to temp file first, then atomic rename
    const tempPath = `${this.dbPath}.tmp`;
    await fs.writeFile(tempPath, JSON.stringify(data, null, 2));
    await fs.rename(tempPath, this.dbPath);
  }
  
  private getStateKey(projectId: string, localPath: string): string {
    return `${projectId}:${localPath}`;
  }
  
  async getFileState(projectId: string, localPath: string): Promise<SyncStateEntry | null> {
    await this.initialize();
    const key = this.getStateKey(projectId, localPath);
    return this.syncStates.get(key) || null;
  }
  
  async saveFileState(entry: SyncStateEntry): Promise<void> {
    await this.initialize();
    const key = this.getStateKey(entry.projectId, entry.localPath);
    this.syncStates.set(key, { ...entry });
    await this.save();
  }
  
  async deleteFileState(projectId: string, localPath: string): Promise<void> {
    await this.initialize();
    const key = this.getStateKey(projectId, localPath);
    this.syncStates.delete(key);
    await this.save();
  }
  
  async listFileStates(projectId: string): Promise<SyncStateEntry[]> {
    await this.initialize();
    return Array.from(this.syncStates.values())
      .filter(entry => entry.projectId === projectId);
  }
  
  async createBackup(entry: BackupEntry): Promise<void> {
    await this.initialize();
    this.backups.set(entry.backupId, { ...entry });
    await this.save();
  }
  
  async listBackups(projectId: string, originalPath?: string): Promise<BackupEntry[]> {
    await this.initialize();
    return Array.from(this.backups.values())
      .filter(backup => {
        if (backup.projectId !== projectId) return false;
        if (originalPath && backup.originalPath !== originalPath) return false;
        return true;
      })
      .sort((a, b) => b.createdAt.getTime() - a.createdAt.getTime());
  }
  
  async deleteBackup(backupId: string): Promise<void> {
    await this.initialize();
    const backup = this.backups.get(backupId);
    if (backup) {
      // Delete the actual backup file
      try {
        await fs.unlink(backup.backupPath);
      } catch (error) {
        // Backup file may not exist, continue
      }
      
      // Remove from database
      this.backups.delete(backupId);
      await this.save();
    }
  }
  
  async cleanupOldBackups(projectId: string, retentionCount: number): Promise<void> {
    await this.initialize();
    
    // Group backups by original path
    const backupsByPath = new Map<string, BackupEntry[]>();
    
    for (const backup of this.backups.values()) {
      if (backup.projectId === projectId) {
        if (!backupsByPath.has(backup.originalPath)) {
          backupsByPath.set(backup.originalPath, []);
        }
        backupsByPath.get(backup.originalPath)!.push(backup);
      }
    }
    
    // Clean up old backups for each file
    for (const [, backupsForFile] of backupsByPath) {
      // Sort by creation time (newest first)
      backupsForFile.sort((a, b) => b.createdAt.getTime() - a.createdAt.getTime());
      
      // Keep only the newest N backups
      const toDelete = backupsForFile.slice(retentionCount);
      
      for (const backup of toDelete) {
        await this.deleteBackup(backup.backupId);
      }
    }
  }
  
  async close(): Promise<void> {
    // For JSON database, just ensure data is saved
    if (this.initialized) {
      await this.save();
    }
  }
}

/**
 * Calculate SHA-256 hash of file content
 */
export async function calculateFileHash(filePath: string): Promise<string> {
  const content = await fs.readFile(filePath);
  return crypto.createHash('sha256').update(content).digest('hex');
}

/**
 * Generate a unique file ID based on project and path
 */
export function generateFileId(projectId: string, localPath: string): string {
  return crypto.createHash('sha256')
    .update(`${projectId}:${localPath}`)
    .digest('hex')
    .substring(0, 16);
}

/**
 * Generate a unique backup ID
 */
export function generateBackupId(): string {
  return crypto.randomBytes(16).toString('hex');
}