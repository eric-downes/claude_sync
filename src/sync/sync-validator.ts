import fs from 'fs/promises';
import path from 'path';
import { 
  SyncStateDatabase, 
  SyncStateEntry, 
  calculateFileHash,
  generateFileId 
} from './sync-state.js';
import { ClaudeAPIClient } from '../api/interfaces.js';

export interface ValidationIssue {
  type: 'error' | 'warning' | 'info';
  code: string;
  message: string;
  filePath?: string;
  suggestion?: string;
}

export interface ConflictInfo {
  filePath: string;
  conflictType: 'local_newer' | 'remote_newer' | 'both_modified' | 'local_deleted' | 'remote_deleted';
  localMtime?: Date;
  remoteMtime?: Date;
  lastSyncTime?: Date;
  localHash?: string;
  remoteHash?: string;
}

export interface ValidationResult {
  isValid: boolean;
  canProceed: boolean;
  issues: ValidationIssue[];
  conflicts: ConflictInfo[];
  stats: {
    localFiles: number;
    remoteFiles: number;
    conflictFiles: number;
    newLocalFiles: number;
    newRemoteFiles: number;
    unchangedFiles: number;
  };
  recommendations: string[];
}

export interface SyncValidatorOptions {
  checkDiskSpace: boolean;
  checkPermissions: boolean;
  checkGitStatus: boolean;
  checkNetworkConnectivity: boolean;
  maxConflictCount: number;
  allowForce: boolean;
}

export class SyncValidator {
  private database: SyncStateDatabase;
  private client: ClaudeAPIClient;
  private projectId: string;
  private localPath: string;
  private options: SyncValidatorOptions;
  
  constructor(
    database: SyncStateDatabase,
    client: ClaudeAPIClient,
    projectId: string,
    localPath: string,
    options: Partial<SyncValidatorOptions> = {}
  ) {
    this.database = database;
    this.client = client;
    this.projectId = projectId;
    this.localPath = localPath;
    this.options = {
      checkDiskSpace: true,
      checkPermissions: true,
      checkGitStatus: true,
      checkNetworkConnectivity: true,
      maxConflictCount: 10,
      allowForce: false,
      ...options
    };
  }
  
  /**
   * Perform comprehensive pre-sync validation
   */
  async validate(direction: 'upload' | 'download' | 'both'): Promise<ValidationResult> {
    const issues: ValidationIssue[] = [];
    const conflicts: ConflictInfo[] = [];
    const stats = {
      localFiles: 0,
      remoteFiles: 0,
      conflictFiles: 0,
      newLocalFiles: 0,
      newRemoteFiles: 0,
      unchangedFiles: 0
    };
    
    try {
      // Basic environment checks
      if (this.options.checkDiskSpace) {
        await this.checkDiskSpace(issues);
      }
      
      if (this.options.checkPermissions) {
        await this.checkPermissions(issues);
      }
      
      if (this.options.checkGitStatus) {
        await this.checkGitStatus(issues);
      }
      
      if (this.options.checkNetworkConnectivity) {
        await this.checkNetworkConnectivity(issues);
      }
      
      // File-level validation
      if (direction === 'upload' || direction === 'both') {
        await this.validateLocalFiles(issues, stats, conflicts);
      }
      
      if (direction === 'download' || direction === 'both') {
        await this.validateRemoteFiles(issues, stats, conflicts);
      }
      
      // Detect conflicts
      if (direction === 'both') {
        await this.detectConflicts(conflicts, stats);
      }
      
    } catch (error) {
      issues.push({
        type: 'error',
        code: 'VALIDATION_ERROR',
        message: `Validation failed: ${error instanceof Error ? error.message : 'Unknown error'}`,
        suggestion: 'Check your configuration and try again'
      });
    }
    
    stats.conflictFiles = conflicts.length;
    
    // Determine if sync can proceed
    const hasErrors = issues.some(issue => issue.type === 'error');
    const tooManyConflicts = conflicts.length > this.options.maxConflictCount;
    const canProceed = !hasErrors && (!tooManyConflicts || this.options.allowForce);
    
    // Generate recommendations
    const recommendations = this.generateRecommendations(issues, conflicts, stats);
    
    return {
      isValid: !hasErrors,
      canProceed,
      issues,
      conflicts,
      stats,
      recommendations
    };
  }
  
  /**
   * Check available disk space
   */
  private async checkDiskSpace(issues: ValidationIssue[]): Promise<void> {
    try {
      const stats = await fs.statfs(this.localPath);
      const availableBytes = stats.bavail * stats.bsize;
      const requiredBytes = 100 * 1024 * 1024; // 100MB minimum
      
      if (availableBytes < requiredBytes) {
        issues.push({
          type: 'error',
          code: 'LOW_DISK_SPACE',
          message: `Insufficient disk space. Available: ${Math.round(availableBytes / 1024 / 1024)}MB, Required: ${Math.round(requiredBytes / 1024 / 1024)}MB`,
          suggestion: 'Free up disk space before syncing'
        });
      } else if (availableBytes < requiredBytes * 2) {
        issues.push({
          type: 'warning',
          code: 'LOW_DISK_SPACE_WARNING',
          message: `Low disk space. Available: ${Math.round(availableBytes / 1024 / 1024)}MB`,
          suggestion: 'Consider freeing up disk space'
        });
      }
    } catch (error) {
      issues.push({
        type: 'warning',
        code: 'DISK_SPACE_CHECK_FAILED',
        message: 'Could not check disk space',
        suggestion: 'Ensure sufficient disk space is available'
      });
    }
  }
  
  /**
   * Check file permissions
   */
  private async checkPermissions(issues: ValidationIssue[]): Promise<void> {
    try {
      // Check if we can read the local directory
      await fs.access(this.localPath, fs.constants.R_OK);
      
      // Check if we can write to the local directory
      await fs.access(this.localPath, fs.constants.W_OK);
      
    } catch (error) {
      issues.push({
        type: 'error',
        code: 'PERMISSION_ERROR',
        message: `Insufficient permissions for ${this.localPath}`,
        suggestion: 'Check file permissions and ensure you have read/write access'
      });
    }
  }
  
  /**
   * Check Git working tree status
   */
  private async checkGitStatus(issues: ValidationIssue[]): Promise<void> {
    try {
      const { exec } = await import('child_process');
      const { promisify } = await import('util');
      const execAsync = promisify(exec);
      
      // Check if we're in a git repository
      try {
        await execAsync('git rev-parse --git-dir', { cwd: this.localPath });
      } catch {
        // Not a git repository, skip git checks
        return;
      }
      
      // Check for uncommitted changes
      const { stdout } = await execAsync('git status --porcelain', { cwd: this.localPath });
      
      if (stdout.trim()) {
        issues.push({
          type: 'warning',
          code: 'GIT_UNCOMMITTED_CHANGES',
          message: 'Git working directory has uncommitted changes',
          suggestion: 'Consider committing changes before syncing for better recovery options'
        });
      }
      
    } catch (error) {
      issues.push({
        type: 'info',
        code: 'GIT_CHECK_FAILED',
        message: 'Could not check Git status',
        suggestion: 'Git checks are optional'
      });
    }
  }
  
  /**
   * Check network connectivity to Claude API
   */
  private async checkNetworkConnectivity(issues: ValidationIssue[]): Promise<void> {
    try {
      // Try to fetch current user info as a connectivity test
      await this.client.getCurrentUser();
    } catch (error) {
      issues.push({
        type: 'error',
        code: 'NETWORK_ERROR',
        message: 'Cannot connect to Claude API',
        suggestion: 'Check your internet connection and API credentials'
      });
    }
  }
  
  /**
   * Validate local files for upload
   */
  private async validateLocalFiles(
    issues: ValidationIssue[], 
    stats: ValidationResult['stats'],
    conflicts: ConflictInfo[]
  ): Promise<void> {
    try {
      const localFiles = await this.getLocalFiles();
      stats.localFiles = localFiles.length;
      
      for (const filePath of localFiles) {
        try {
          const relativePath = path.relative(this.localPath, filePath);
          const fileState = await this.database.getFileState(this.projectId, relativePath);
          
          if (!fileState) {
            stats.newLocalFiles++;
          } else {
            // Check if file has been modified since last sync
            const currentHash = await calculateFileHash(filePath);
            if (currentHash !== fileState.localHash) {
              // File has been modified locally
              const fileStat = await fs.stat(filePath);
              if (fileState.remoteMtime && fileStat.mtime > fileState.lastSyncTime) {
                // Potential conflict if remote also modified
                conflicts.push({
                  filePath: relativePath,
                  conflictType: 'local_newer',
                  localMtime: fileStat.mtime,
                  remoteMtime: fileState.remoteMtime,
                  lastSyncTime: fileState.lastSyncTime,
                  localHash: currentHash,
                  remoteHash: fileState.remoteHash
                });
              }
            } else {
              stats.unchangedFiles++;
            }
          }
          
        } catch (fileError) {
          issues.push({
            type: 'warning',
            code: 'FILE_READ_ERROR',
            message: `Cannot read file: ${path.relative(this.localPath, filePath)}`,
            filePath: filePath,
            suggestion: 'Check file permissions'
          });
        }
      }
      
    } catch (error) {
      issues.push({
        type: 'error',
        code: 'LOCAL_SCAN_ERROR',
        message: `Cannot scan local files: ${error instanceof Error ? error.message : 'Unknown error'}`,
        suggestion: 'Check local directory permissions'
      });
    }
  }
  
  /**
   * Validate remote files for download
   */
  private async validateRemoteFiles(
    issues: ValidationIssue[], 
    stats: ValidationResult['stats'],
    conflicts: ConflictInfo[]
  ): Promise<void> {
    try {
      const remoteFiles = await this.client.listKnowledgeFiles(this.projectId);
      stats.remoteFiles = remoteFiles.length;
      
      for (const remoteFile of remoteFiles) {
        const fileState = await this.database.getFileState(this.projectId, remoteFile.path);
        
        if (!fileState) {
          stats.newRemoteFiles++;
        } else {
          // Check if remote file has been modified
          const remoteMtime = new Date(remoteFile.updatedAt);
          if (remoteMtime > fileState.lastSyncTime) {
            // Remote file has been modified
            const localPath = path.join(this.localPath, remoteFile.path);
            
            try {
              const localStat = await fs.stat(localPath);
              if (localStat.mtime > fileState.lastSyncTime) {
                // Both local and remote modified - conflict
                conflicts.push({
                  filePath: remoteFile.path,
                  conflictType: 'both_modified',
                  localMtime: localStat.mtime,
                  remoteMtime,
                  lastSyncTime: fileState.lastSyncTime
                });
              } else {
                // Only remote modified
                conflicts.push({
                  filePath: remoteFile.path,
                  conflictType: 'remote_newer',
                  remoteMtime,
                  lastSyncTime: fileState.lastSyncTime
                });
              }
            } catch {
              // Local file doesn't exist
              conflicts.push({
                filePath: remoteFile.path,
                conflictType: 'local_deleted',
                remoteMtime,
                lastSyncTime: fileState.lastSyncTime
              });
            }
          }
        }
      }
      
    } catch (error) {
      issues.push({
        type: 'error',
        code: 'REMOTE_SCAN_ERROR',
        message: `Cannot scan remote files: ${error instanceof Error ? error.message : 'Unknown error'}`,
        suggestion: 'Check API credentials and network connection'
      });
    }
  }
  
  /**
   * Detect conflicts between local and remote files
   */
  private async detectConflicts(
    conflicts: ConflictInfo[], 
    stats: ValidationResult['stats']
  ): Promise<void> {
    // This method combines the conflict detection from validateLocalFiles and validateRemoteFiles
    // The actual conflict detection logic is implemented in those methods
    
    // Check for deleted files that still exist remotely
    const fileStates = await this.database.listFileStates(this.projectId);
    const remoteFiles = await this.client.listKnowledgeFiles(this.projectId);
    const remoteFilePaths = new Set(remoteFiles.map(f => f.path));
    
    for (const fileState of fileStates) {
      const localPath = path.join(this.localPath, fileState.localPath);
      
      try {
        await fs.access(localPath);
        // Local file exists
      } catch {
        // Local file deleted
        if (remoteFilePaths.has(fileState.localPath)) {
          // Remote still exists
          conflicts.push({
            filePath: fileState.localPath,
            conflictType: 'local_deleted',
            lastSyncTime: fileState.lastSyncTime
          });
        }
      }
    }
  }
  
  /**
   * Get list of local files to sync
   */
  private async getLocalFiles(): Promise<string[]> {
    const files: string[] = [];
    
    async function scanDirectory(dir: string): Promise<void> {
      const entries = await fs.readdir(dir, { withFileTypes: true });
      
      for (const entry of entries) {
        const fullPath = path.join(dir, entry.name);
        
        if (entry.isDirectory()) {
          // Skip common ignore patterns
          if (!['node_modules', '.git', 'dist', '.claude-sync'].includes(entry.name)) {
            await scanDirectory(fullPath);
          }
        } else if (entry.isFile()) {
          // Skip common ignore patterns
          if (!entry.name.endsWith('.log') && !entry.name.startsWith('.')) {
            files.push(fullPath);
          }
        }
      }
    }
    
    await scanDirectory(this.localPath);
    return files;
  }
  
  /**
   * Generate recommendations based on validation results
   */
  private generateRecommendations(
    issues: ValidationIssue[], 
    conflicts: ConflictInfo[], 
    stats: ValidationResult['stats']
  ): string[] {
    const recommendations: string[] = [];
    
    if (conflicts.length > 0) {
      recommendations.push('Review conflicts before proceeding');
      recommendations.push('Consider using --dry-run to preview changes');
      
      if (conflicts.length > 5) {
        recommendations.push('Consider syncing in smaller batches');
      }
    }
    
    if (stats.newLocalFiles > 0 || stats.newRemoteFiles > 0) {
      recommendations.push('Enable backups for safety');
    }
    
    const hasErrors = issues.some(issue => issue.type === 'error');
    if (hasErrors) {
      recommendations.push('Fix errors before attempting sync');
    }
    
    const hasWarnings = issues.some(issue => issue.type === 'warning');
    if (hasWarnings) {
      recommendations.push('Address warnings for optimal sync experience');
    }
    
    if (stats.localFiles > 100 || stats.remoteFiles > 100) {
      recommendations.push('Large number of files detected - sync may take some time');
    }
    
    return recommendations;
  }
}