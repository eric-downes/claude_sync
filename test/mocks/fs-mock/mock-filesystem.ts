/**
 * Mock filesystem for testing file operations
 */
import { EventEmitter } from 'events';
import path from 'path';

interface MockFile {
  content: string;
  mtime: Date;
  size: number;
}

interface MockDirectory {
  files: Map<string, MockFile>;
  directories: Map<string, MockDirectory>;
  mtime: Date;
}

export class MockFileSystem extends EventEmitter {
  private root: MockDirectory;
  
  constructor() {
    super();
    this.root = this.createDirectory();
  }
  
  /**
   * Create a mock directory
   */
  private createDirectory(): MockDirectory {
    return {
      files: new Map<string, MockFile>(),
      directories: new Map<string, MockDirectory>(),
      mtime: new Date()
    };
  }
  
  /**
   * Get a directory by path
   */
  private getDirectoryByPath(dirPath: string): MockDirectory | null {
    if (dirPath === '/' || dirPath === '') {
      return this.root;
    }
    
    const parts = dirPath.split('/').filter(Boolean);
    let current = this.root;
    
    for (const part of parts) {
      const next = current.directories.get(part);
      if (!next) {
        return null;
      }
      current = next;
    }
    
    return current;
  }
  
  /**
   * Create a directory
   */
  mkdir(dirPath: string): void {
    const parentPath = path.dirname(dirPath);
    const dirName = path.basename(dirPath);
    
    if (dirName === '') {
      return;
    }
    
    const parent = this.getDirectoryByPath(parentPath);
    if (!parent) {
      throw new Error(`Parent directory does not exist: ${parentPath}`);
    }
    
    if (parent.directories.has(dirName)) {
      throw new Error(`Directory already exists: ${dirPath}`);
    }
    
    parent.directories.set(dirName, this.createDirectory());
    parent.mtime = new Date();
  }
  
  /**
   * Create a directory recursively
   */
  mkdirp(dirPath: string): void {
    const parts = dirPath.split('/').filter(Boolean);
    let currentPath = '';
    
    for (const part of parts) {
      currentPath = path.join(currentPath, part);
      
      try {
        this.mkdir(currentPath);
      } catch (error) {
        // Ignore "already exists" errors
        if (!(error instanceof Error && error.message.includes('already exists'))) {
          throw error;
        }
      }
    }
  }
  
  /**
   * Write a file
   */
  writeFile(filePath: string, content: string): void {
    const dirPath = path.dirname(filePath);
    const fileName = path.basename(filePath);
    
    // Ensure directory exists
    this.mkdirp(dirPath);
    
    const dir = this.getDirectoryByPath(dirPath);
    if (!dir) {
      throw new Error(`Directory does not exist: ${dirPath}`);
    }
    
    const now = new Date();
    const file: MockFile = {
      content,
      mtime: now,
      size: content.length
    };
    
    const existingFile = dir.files.get(fileName);
    dir.files.set(fileName, file);
    dir.mtime = now;
    
    // Emit change event
    if (existingFile) {
      this.emit('change', filePath, content);
    } else {
      this.emit('add', filePath, content);
    }
  }
  
  /**
   * Read a file
   */
  readFile(filePath: string): string {
    const dirPath = path.dirname(filePath);
    const fileName = path.basename(filePath);
    
    const dir = this.getDirectoryByPath(dirPath);
    if (!dir) {
      throw new Error(`Directory does not exist: ${dirPath}`);
    }
    
    const file = dir.files.get(fileName);
    if (!file) {
      throw new Error(`File does not exist: ${filePath}`);
    }
    
    return file.content;
  }
  
  /**
   * Check if file exists
   */
  existsSync(filePath: string): boolean {
    try {
      const dirPath = path.dirname(filePath);
      const fileName = path.basename(filePath);
      
      const dir = this.getDirectoryByPath(dirPath);
      if (!dir) {
        return false;
      }
      
      return dir.files.has(fileName);
    } catch (error) {
      return false;
    }
  }
  
  /**
   * Delete a file
   */
  unlinkSync(filePath: string): void {
    const dirPath = path.dirname(filePath);
    const fileName = path.basename(filePath);
    
    const dir = this.getDirectoryByPath(dirPath);
    if (!dir) {
      throw new Error(`Directory does not exist: ${dirPath}`);
    }
    
    if (!dir.files.has(fileName)) {
      throw new Error(`File does not exist: ${filePath}`);
    }
    
    dir.files.delete(fileName);
    dir.mtime = new Date();
    
    // Emit unlink event
    this.emit('unlink', filePath);
  }
  
  /**
   * List files in a directory
   */
  readdirSync(dirPath: string): string[] {
    const dir = this.getDirectoryByPath(dirPath);
    if (!dir) {
      throw new Error(`Directory does not exist: ${dirPath}`);
    }
    
    const fileNames = Array.from(dir.files.keys());
    const dirNames = Array.from(dir.directories.keys());
    
    return [...fileNames, ...dirNames];
  }
  
  /**
   * Get file stats
   */
  statSync(filePath: string): { 
    isFile: () => boolean; 
    isDirectory: () => boolean;
    mtime: Date;
    size: number;
  } {
    const dirPath = path.dirname(filePath);
    const name = path.basename(filePath);
    
    const dir = this.getDirectoryByPath(dirPath);
    if (!dir) {
      throw new Error(`Directory does not exist: ${dirPath}`);
    }
    
    // Check if it's a file
    const file = dir.files.get(name);
    if (file) {
      return {
        isFile: () => true,
        isDirectory: () => false,
        mtime: file.mtime,
        size: file.size
      };
    }
    
    // Check if it's a directory
    const childDir = dir.directories.get(name);
    if (childDir) {
      return {
        isFile: () => false,
        isDirectory: () => true,
        mtime: childDir.mtime,
        size: 0
      };
    }
    
    throw new Error(`No such file or directory: ${filePath}`);
  }
  
  /**
   * Watch a directory for changes
   */
  watch(
    dirPath: string, 
    callback: (eventType: string, filename: string) => void
  ): { close: () => void } {
    const listener = (eventType: string, filePath: string) => {
      // Only trigger if the file is in the watched directory
      if (filePath.startsWith(dirPath)) {
        const relativePath = path.relative(dirPath, filePath);
        callback(eventType, relativePath);
      }
    };
    
    this.on('add', (filePath, content) => listener('add', filePath));
    this.on('change', (filePath, content) => listener('change', filePath));
    this.on('unlink', (filePath) => listener('unlink', filePath));
    
    return {
      close: () => {
        this.removeAllListeners('add');
        this.removeAllListeners('change');
        this.removeAllListeners('unlink');
      }
    };
  }
}