import fs from 'fs/promises';
import path from 'path';
import { 
  SyncStateDatabase, 
  JsonSyncStateDatabase, 
  SyncStateEntry,
  calculateFileHash,
  generateFileId 
} from './sync-state.js';
import { BackupManager, BackupOptions } from './backup-manager.js';
import { SyncValidator, ValidationResult, ConflictInfo } from './sync-validator.js';
import { ClaudeAPIClient } from '../api/interfaces.js';

export interface SafeSyncOptions {
  direction: 'upload' | 'download' | 'both';
  dryRun: boolean;
  backup: BackupOptions;
  validation: {
    enabled: boolean;
    checkDiskSpace: boolean;
    checkPermissions: boolean;
    checkGitStatus: boolean;
    checkNetworkConnectivity: boolean;
    maxConflictCount: number;
  };
  conflictResolution: 'ask' | 'skip' | 'local_wins' | 'remote_wins' | 'backup_and_merge';
  force: boolean;
  verbose: boolean;
  excludePatterns: string[];
}

export interface SyncOperation {
  type: 'upload' | 'download' | 'delete_local' | 'delete_remote';
  filePath: string;
  reason: string;
  conflictType?: string;
  backupRequired: boolean;
}

export interface SyncResult {
  success: boolean;
  dryRun: boolean;
  operations: SyncOperation[];
  executedOperations: SyncOperation[];
  skippedOperations: SyncOperation[];
  errors: string[];
  warnings: string[];
  stats: {
    filesUploaded: number;
    filesDownloaded: number;
    filesSkipped: number;
    conflictsResolved: number;
    backupsCreated: number;
    totalOperations: number;
    duration: number;
  };
  validationResult?: ValidationResult;
}

export class SafeSync {
  private database: SyncStateDatabase;
  private backupManager: BackupManager;
  private validator: SyncValidator;
  private client: ClaudeAPIClient;
  private projectId: string;
  private localPath: string;
  private options: SafeSyncOptions;
  
  constructor(
    client: ClaudeAPIClient,
    projectId: string,
    localPath: string,
    options: Partial<SafeSyncOptions> = {}
  ) {
    this.client = client;
    this.projectId = projectId;
    this.localPath = localPath;
    
    // Initialize with defaults
    this.options = {
      direction: 'both',
      dryRun: false,
      backup: {
        enabled: true,
        retentionCount: 5,
        compressionLevel: 0,
        location: 'local',
        autoCleanup: true
      },
      validation: {
        enabled: true,
        checkDiskSpace: true,
        checkPermissions: true,
        checkGitStatus: true,
        checkNetworkConnectivity: true,
        maxConflictCount: 10
      },
      conflictResolution: 'ask',
      force: false,
      verbose: false,
      excludePatterns: ['node_modules/**', '.git/**', '*.log', '.claude-sync/**'],
      ...options
    };
    
    // Initialize components
    this.database = new JsonSyncStateDatabase(projectId);
    this.backupManager = new BackupManager(this.database, projectId, this.options.backup);
    this.validator = new SyncValidator(
      this.database, 
      this.client, 
      projectId, 
      localPath,
      {
        ...this.options.validation,
        allowForce: this.options.force
      }
    );
  }
  
  /**
   * Perform safe synchronization with full validation and backup support
   */
  async sync(): Promise<SyncResult> {
    const startTime = Date.now();
    const result: SyncResult = {
      success: false,
      dryRun: this.options.dryRun,
      operations: [],
      executedOperations: [],
      skippedOperations: [],
      errors: [],
      warnings: [],
      stats: {
        filesUploaded: 0,
        filesDownloaded: 0,
        filesSkipped: 0,
        conflictsResolved: 0,
        backupsCreated: 0,
        totalOperations: 0,
        duration: 0
      }
    };
    
    try {
      // Initialize database
      await this.database.initialize();
      
      // Step 1: Pre-sync validation
      if (this.options.validation.enabled) {
        if (this.options.verbose) {
          console.log('🔍 Running pre-sync validation...');
        }
        
        const validationResult = await this.validator.validate(this.options.direction);
        result.validationResult = validationResult;
        
        if (!validationResult.canProceed && !this.options.force) {
          result.errors.push('Validation failed. Use --force to override.');
          result.stats.duration = Date.now() - startTime;
          return result;
        }
        
        if (validationResult.issues.length > 0) {
          for (const issue of validationResult.issues) {
            if (issue.type === 'error') {
              result.errors.push(issue.message);
            } else if (issue.type === 'warning') {
              result.warnings.push(issue.message);
            }
          }
        }
      }
      
      // Step 2: Plan operations
      if (this.options.verbose) {
        console.log('📋 Planning sync operations...');
      }
      
      await this.planOperations(result);
      
      // Step 3: Handle conflicts
      if (result.validationResult?.conflicts && result.validationResult.conflicts.length > 0) {
        await this.handleConflicts(result.validationResult.conflicts, result);
      }
      
      // Step 4: Execute operations (unless dry-run)
      if (!this.options.dryRun) {
        if (this.options.verbose) {
          console.log(`🚀 Executing ${result.operations.length} operations...`);
        }
        
        await this.executeOperations(result);
      } else {
        if (this.options.verbose) {
          console.log(`🏃 Dry run: ${result.operations.length} operations planned (not executed)`);
        }
      }
      
      result.success = result.errors.length === 0;
      result.stats.duration = Date.now() - startTime;
      
      return result;
      
    } catch (error) {
      result.errors.push(`Sync failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
      result.stats.duration = Date.now() - startTime;
      return result;
    } finally {
      await this.database.close();
    }
  }
  
  /**
   * Plan all sync operations
   */
  private async planOperations(result: SyncResult): Promise<void> {
    const operations: SyncOperation[] = [];
    
    // Plan uploads
    if (this.options.direction === 'upload' || this.options.direction === 'both') {
      const uploadOps = await this.planUploadOperations();
      operations.push(...uploadOps);
    }
    
    // Plan downloads
    if (this.options.direction === 'download' || this.options.direction === 'both') {
      const downloadOps = await this.planDownloadOperations();
      operations.push(...downloadOps);
    }
    
    result.operations = operations;
    result.stats.totalOperations = operations.length;
  }
  
  /**
   * Plan upload operations for local files
   */
  private async planUploadOperations(): Promise<SyncOperation[]> {
    const operations: SyncOperation[] = [];
    const localFiles = await this.getLocalFiles();
    
    for (const filePath of localFiles) {
      const relativePath = path.relative(this.localPath, filePath);
      const fileState = await this.database.getFileState(this.projectId, relativePath);
      
      try {
        const currentHash = await calculateFileHash(filePath);
        
        if (!fileState) {
          // New file
          operations.push({
            type: 'upload',
            filePath: relativePath,
            reason: 'New local file',
            backupRequired: false
          });
        } else if (currentHash !== fileState.localHash) {
          // Modified file
          operations.push({
            type: 'upload',
            filePath: relativePath,
            reason: 'Local file modified',
            backupRequired: true
          });
        }
        
      } catch (error) {
        // Skip files we can't read
        continue;
      }
    }
    
    return operations;
  }
  
  /**
   * Plan download operations for remote files
   */
  private async planDownloadOperations(): Promise<SyncOperation[]> {
    const operations: SyncOperation[] = [];
    
    try {
      const remoteFiles = await this.client.listKnowledgeFiles(this.projectId);
      
      for (const remoteFile of remoteFiles) {
        const fileState = await this.database.getFileState(this.projectId, remoteFile.path);
        const localFilePath = path.join(this.localPath, remoteFile.path);
        
        if (!fileState) {
          // New remote file
          operations.push({
            type: 'download',
            filePath: remoteFile.path,
            reason: 'New remote file',
            backupRequired: false
          });
        } else {
          const remoteMtime = new Date(remoteFile.updatedAt);
          if (remoteMtime > fileState.lastSyncTime) {
            // Remote file modified
            const localExists = await this.fileExists(localFilePath);
            
            operations.push({
              type: 'download',
              filePath: remoteFile.path,
              reason: 'Remote file modified',
              backupRequired: localExists
            });
          }
        }
      }
      
    } catch (error) {
      throw new Error(`Failed to list remote files: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
    
    return operations;
  }
  
  /**
   * Handle conflicts based on resolution strategy
   */
  private async handleConflicts(conflicts: ConflictInfo[], result: SyncResult): Promise<void> {
    for (const conflict of conflicts) {
      switch (this.options.conflictResolution) {
        case 'skip':
          result.operations = result.operations.filter(op => op.filePath !== conflict.filePath);
          result.warnings.push(`Skipped conflicted file: ${conflict.filePath}`);
          break;
          
        case 'local_wins':
          // Keep upload operation, remove download operation
          result.operations = result.operations.filter(op => 
            !(op.type === 'download' && op.filePath === conflict.filePath)
          );
          break;
          
        case 'remote_wins':
          // Keep download operation, remove upload operation
          result.operations = result.operations.filter(op => 
            !(op.type === 'upload' && op.filePath === conflict.filePath)
          );
          break;
          
        case 'backup_and_merge':
          // Create backup and let both operations proceed
          const uploadOp = result.operations.find(op => op.type === 'upload' && op.filePath === conflict.filePath);
          if (uploadOp) {
            uploadOp.backupRequired = true;
            uploadOp.reason += ' (conflict - backup created)';
          }
          break;
          
        case 'ask':
        default:
          // In CLI, this would prompt the user
          // For now, default to skip
          result.operations = result.operations.filter(op => op.filePath !== conflict.filePath);
          result.warnings.push(`Skipped conflicted file (interactive resolution not implemented): ${conflict.filePath}`);
          break;
      }
      
      result.stats.conflictsResolved++;
    }
  }
  
  /**
   * Execute all planned operations
   */
  private async executeOperations(result: SyncResult): Promise<void> {
    for (const operation of result.operations) {
      try {
        // Create backup if required
        if (operation.backupRequired) {
          const localFilePath = path.join(this.localPath, operation.filePath);
          const backupResult = await this.backupManager.createBackup(localFilePath, 'sync');
          
          if (backupResult.success) {
            result.stats.backupsCreated++;
            if (this.options.verbose) {
              console.log(`📦 Created backup: ${operation.filePath}`);
            }
          } else {
            result.warnings.push(`Failed to create backup for ${operation.filePath}: ${backupResult.error}`);
          }
        }
        
        // Execute the operation
        await this.executeOperation(operation, result);
        result.executedOperations.push(operation);
        
      } catch (error) {
        result.errors.push(`Failed to execute ${operation.type} for ${operation.filePath}: ${error instanceof Error ? error.message : 'Unknown error'}`);
        result.skippedOperations.push(operation);
      }
    }
  }
  
  /**
   * Execute a single operation
   */
  private async executeOperation(operation: SyncOperation, result: SyncResult): Promise<void> {
    switch (operation.type) {
      case 'upload':
        await this.executeUpload(operation, result);
        break;
        
      case 'download':
        await this.executeDownload(operation, result);
        break;
        
      case 'delete_local':
        await this.executeLocalDelete(operation, result);
        break;
        
      case 'delete_remote':
        await this.executeRemoteDelete(operation, result);
        break;
    }
  }
  
  /**
   * Execute file upload
   */
  private async executeUpload(operation: SyncOperation, result: SyncResult): Promise<void> {
    const localFilePath = path.join(this.localPath, operation.filePath);
    const content = await fs.readFile(localFilePath, 'utf-8');
    
    // Upload to remote
    const uploadedFile = await this.client.uploadKnowledgeFile(this.projectId, operation.filePath, content);
    
    // Update sync state
    const fileStats = await fs.stat(localFilePath);
    const fileHash = await calculateFileHash(localFilePath);
    
    const syncState: SyncStateEntry = {
      fileId: generateFileId(this.projectId, operation.filePath),
      projectId: this.projectId,
      localPath: operation.filePath,
      remoteId: uploadedFile.id,
      localHash: fileHash,
      remoteHash: fileHash, // Assume same content
      localMtime: fileStats.mtime,
      remoteMtime: new Date(uploadedFile.updatedAt),
      lastSyncTime: new Date(),
      syncDirection: 'upload',
      conflictState: 'none',
      size: fileStats.size,
      isDeleted: false
    };
    
    await this.database.saveFileState(syncState);
    result.stats.filesUploaded++;
    
    if (this.options.verbose) {
      console.log(`⬆️  Uploaded: ${operation.filePath}`);
    }
  }
  
  /**
   * Execute file download
   */
  private async executeDownload(operation: SyncOperation, result: SyncResult): Promise<void> {
    // Get file content from remote
    const remoteFiles = await this.client.listKnowledgeFiles(this.projectId);
    const remoteFile = remoteFiles.find(f => f.path === operation.filePath);
    
    if (!remoteFile) {
      throw new Error(`Remote file not found: ${operation.filePath}`);
    }
    
    const fileContent = await this.client.getKnowledgeFile(this.projectId, remoteFile.id);
    const localFilePath = path.join(this.localPath, operation.filePath);
    
    // Ensure directory exists
    await fs.mkdir(path.dirname(localFilePath), { recursive: true });
    
    // Write file
    await fs.writeFile(localFilePath, fileContent.content || '');
    
    // Update sync state
    const fileStats = await fs.stat(localFilePath);
    const fileHash = await calculateFileHash(localFilePath);
    
    const syncState: SyncStateEntry = {
      fileId: generateFileId(this.projectId, operation.filePath),
      projectId: this.projectId,
      localPath: operation.filePath,
      remoteId: remoteFile.id,
      localHash: fileHash,
      remoteHash: fileHash, // Assume same content
      localMtime: fileStats.mtime,
      remoteMtime: new Date(remoteFile.updatedAt),
      lastSyncTime: new Date(),
      syncDirection: 'download',
      conflictState: 'none',
      size: fileStats.size,
      isDeleted: false
    };
    
    await this.database.saveFileState(syncState);
    result.stats.filesDownloaded++;
    
    if (this.options.verbose) {
      console.log(`⬇️  Downloaded: ${operation.filePath}`);
    }
  }
  
  /**
   * Execute local file deletion
   */
  private async executeLocalDelete(operation: SyncOperation, result: SyncResult): Promise<void> {
    const localFilePath = path.join(this.localPath, operation.filePath);
    
    // Create backup before deletion
    if (await this.fileExists(localFilePath)) {
      await this.backupManager.createBackup(localFilePath, 'delete');
      await fs.unlink(localFilePath);
      
      if (this.options.verbose) {
        console.log(`🗑️  Deleted local: ${operation.filePath}`);
      }
    }
    
    // Mark as deleted in sync state
    const fileState = await this.database.getFileState(this.projectId, operation.filePath);
    if (fileState) {
      fileState.isDeleted = true;
      fileState.lastSyncTime = new Date();
      await this.database.saveFileState(fileState);
    }
  }
  
  /**
   * Execute remote file deletion
   */
  private async executeRemoteDelete(operation: SyncOperation, result: SyncResult): Promise<void> {
    const fileState = await this.database.getFileState(this.projectId, operation.filePath);
    
    if (fileState?.remoteId) {
      await this.client.deleteKnowledgeFile(this.projectId, fileState.remoteId);
      
      if (this.options.verbose) {
        console.log(`🗑️  Deleted remote: ${operation.filePath}`);
      }
      
      // Mark as deleted in sync state
      fileState.isDeleted = true;
      fileState.lastSyncTime = new Date();
      await this.database.saveFileState(fileState);
    }
  }
  
  /**
   * Get list of local files to sync
   */
  private async getLocalFiles(): Promise<string[]> {
    const files: string[] = [];
    
    async function scanDirectory(dir: string, excludePatterns: string[]): Promise<void> {
      const entries = await fs.readdir(dir, { withFileTypes: true });
      
      for (const entry of entries) {
        const fullPath = path.join(dir, entry.name);
        const relativePath = path.relative(process.cwd(), fullPath);
        
        // Check exclude patterns
        const isExcluded = excludePatterns.some(pattern => {
          if (pattern.includes('**')) {
            return relativePath.includes(pattern.replace('/**', ''));
          }
          return relativePath.includes(pattern.replace('*', ''));
        });
        
        if (isExcluded) continue;
        
        if (entry.isDirectory()) {
          await scanDirectory(fullPath, excludePatterns);
        } else if (entry.isFile()) {
          files.push(fullPath);
        }
      }
    }
    
    await scanDirectory(this.localPath, this.options.excludePatterns);
    return files;
  }
  
  /**
   * Check if a file exists
   */
  private async fileExists(filePath: string): Promise<boolean> {
    try {
      await fs.access(filePath);
      return true;
    } catch {
      return false;
    }
  }
}