/**
 * File tracker for Claude Sync
 * Watches for file changes, additions, and deletions
 */

import { EventEmitter } from 'events';
import path from 'path';
import chokidar from 'chokidar';

/**
 * FileTracker - Tracks file changes in a directory
 * Uses chokidar for efficient and reliable file watching
 */
export class FileTracker extends EventEmitter {
  constructor(directory, options = {}) {
    super();
    this.directory = directory;
    this.options = {
      ignore: ['**/node_modules/**', '**/.git/**', '**/dist/**'],
      ...options
    };
    this.watcher = null;
    this.files = new Map();
    this.isWatching = false;
  }

  /**
   * Start tracking files in the specified directory
   * @returns {Promise<boolean>} True if tracking started successfully
   */
  async start() {
    if (this.isWatching) {
      return true;
    }

    try {
      // Initialize the watcher with chokidar
      this.watcher = chokidar.watch(this.directory, {
        ignored: this.options.ignore,
        persistent: true,
        ignoreInitial: false,
        awaitWriteFinish: {
          stabilityThreshold: 300,
          pollInterval: 100
        }
      });

      // Set up event handlers
      if (this.watcher && typeof this.watcher.on === 'function') {
        this.watcher
          .on('add', (filePath) => this.handleFileAdd(filePath))
          .on('change', (filePath) => this.handleFileChange(filePath))
          .on('unlink', (filePath) => this.handleFileUnlink(filePath))
          .on('error', (error) => this.emit('error', error));
      }

      this.isWatching = true;
      return true;
    } catch (error) {
      this.emit('error', error);
      return false;
    }
  }

  /**
   * Handle file addition events
   * @param {string} filePath - Path to the added file
   */
  handleFileAdd(filePath) {
    try {
      const relativePath = path.relative(this.directory, filePath);
      const fileInfo = {
        path: filePath,
        relativePath,
        mtime: new Date(),
        lastSynced: null
      };
      
      this.files.set(filePath, fileInfo);
      this.emit('add', filePath, fileInfo);
    } catch (error) {
      this.emit('error', error);
    }
  }

  /**
   * Handle file change events
   * @param {string} filePath - Path to the changed file
   */
  handleFileChange(filePath) {
    try {
      const relativePath = path.relative(this.directory, filePath);
      const fileInfo = {
        path: filePath,
        relativePath,
        mtime: new Date(),
        lastSynced: this.files.get(filePath)?.lastSynced || null
      };
      
      this.files.set(filePath, fileInfo);
      this.emit('change', filePath, fileInfo);
    } catch (error) {
      this.emit('error', error);
    }
  }

  /**
   * Handle file deletion events
   * @param {string} filePath - Path to the deleted file
   */
  handleFileUnlink(filePath) {
    try {
      this.files.delete(filePath);
      this.emit('unlink', filePath);
    } catch (error) {
      this.emit('error', error);
    }
  }

  /**
   * Add a specific file or directory to be tracked
   * @param {string} filePath - Path to the file or directory
   */
  add(filePath) {
    if (!this.watcher) {
      return false;
    }
    
    this.watcher.add(filePath);
    return true;
  }

  /**
   * Stop tracking a specific file or directory
   * @param {string} filePath - Path to the file or directory
   */
  unwatch(filePath) {
    if (!this.watcher) {
      return false;
    }
    
    this.watcher.unwatch(filePath);
    return true;
  }

  /**
   * Get all tracked files
   * @returns {Map} Map of tracked files
   */
  getFiles() {
    return this.files;
  }

  /**
   * Mark a file as synced
   * @param {string} filePath - Path to the file
   */
  markSynced(filePath) {
    const fileInfo = this.files.get(filePath);
    
    if (fileInfo) {
      fileInfo.lastSynced = new Date();
      this.files.set(filePath, fileInfo);
    }
  }

  /**
   * Stop tracking all files and clean up resources
   * @returns {boolean} True if tracking stopped successfully
   */
  close() {
    if (!this.watcher) {
      return true;
    }
    
    try {
      this.watcher.close();
      this.watcher = null;
      this.files.clear();
      this.isWatching = false;
      return true;
    } catch (error) {
      this.emit('error', error);
      return false;
    }
  }
}

export default FileTracker;