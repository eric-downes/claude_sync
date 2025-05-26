import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { syncFiles } from '../sync/sync.js';
import * as configure from '../config/configure.js';
import * as claude from '../api/claude.js';

// Mock the dependencies
vi.mock('../config/configure.js');
vi.mock('../api/claude.js');
vi.mock('fs/promises', async (importOriginal) => {
  return {
    readdir: vi.fn(),
    readFile: vi.fn(),
    writeFile: vi.fn(),
    mkdir: vi.fn(),
    default: {
      readdir: vi.fn(),
      readFile: vi.fn(),
      writeFile: vi.fn(),
      mkdir: vi.fn(),
    }
  };
});

describe('Sync Module', () => {
  const mockProjectConfig = {
    projectName: 'test-project',
    projectId: 'test-project-123',
    localPath: '/mock/project/path',
    excludePatterns: ['node_modules/**', '.git/**']
  };

  const mockFiles = [
    { 
      id: 'file1', 
      name: 'main.ts', 
      path: 'src/main.ts', 
      content: 'console.log("test");',
      sizeBytes: 25,
      mimeType: 'text/typescript',
      createdAt: '2024-01-01T00:00:00Z',
      updatedAt: '2024-01-01T00:00:00Z'
    },
    { 
      id: 'file2', 
      name: 'README.md', 
      path: 'README.md', 
      content: '# Test Project',
      sizeBytes: 15,
      mimeType: 'text/markdown',
      createdAt: '2024-01-01T00:00:00Z',
      updatedAt: '2024-01-01T00:00:00Z'
    }
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    
    // Mock console methods to suppress output during tests
    vi.spyOn(console, 'log').mockImplementation(() => {});
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should throw error if project not found', async () => {
    // Mock getProjectConfig to return null
    vi.mocked(configure.getProjectConfig).mockReturnValue(null);

    await expect(syncFiles('nonexistent-project')).rejects.toThrow(
      'Project "nonexistent-project" not found. Please configure it first.'
    );
  });
  
  it('should sync in upload direction only', async () => {
    // Mock project config
    vi.mocked(configure.getProjectConfig).mockReturnValue(mockProjectConfig);
    vi.mocked(configure.updateLastSynced).mockImplementation(() => {});
    
    // Mock file system
    const fs = await import('fs/promises');
    vi.mocked(fs.default.readdir).mockResolvedValue([
      { name: 'test.txt', isDirectory: () => false } as any
    ]);
    vi.mocked(fs.default.readFile).mockResolvedValue('file content');
    
    // Mock API calls
    vi.mocked(claude.uploadFileToProject).mockResolvedValue(undefined);
    vi.mocked(claude.downloadFilesFromProject).mockResolvedValue([]);

    await syncFiles('test-project', 'upload');

    // Verify upload was called but download was not
    expect(claude.uploadFileToProject).toHaveBeenCalled();
    expect(claude.downloadFilesFromProject).not.toHaveBeenCalled();
    expect(configure.updateLastSynced).toHaveBeenCalledWith('test-project');
  });
  
  it('should sync in download direction only', async () => {
    // Mock project config
    vi.mocked(configure.getProjectConfig).mockReturnValue(mockProjectConfig);
    vi.mocked(configure.updateLastSynced).mockImplementation(() => {});
    
    // Mock API calls
    vi.mocked(claude.uploadFileToProject).mockResolvedValue(undefined);
    vi.mocked(claude.downloadFilesFromProject).mockResolvedValue(mockFiles);
    
    // Mock file system
    const fs = await import('fs/promises');
    vi.mocked(fs.default.mkdir).mockResolvedValue(undefined);
    vi.mocked(fs.default.writeFile).mockResolvedValue(undefined);

    await syncFiles('test-project', 'download');

    // Verify download was called but upload was not
    expect(claude.downloadFilesFromProject).toHaveBeenCalledWith(mockProjectConfig.projectId);
    expect(claude.uploadFileToProject).not.toHaveBeenCalled();
    expect(fs.default.writeFile).toHaveBeenCalledTimes(2); // Two mock files
    expect(configure.updateLastSynced).toHaveBeenCalledWith('test-project');
  });
  
  it('should sync in both directions by default', async () => {
    // Mock project config
    vi.mocked(configure.getProjectConfig).mockReturnValue(mockProjectConfig);
    vi.mocked(configure.updateLastSynced).mockImplementation(() => {});
    
    // Mock file system for upload
    const fs = await import('fs/promises');
    vi.mocked(fs.default.readdir).mockResolvedValue([
      { name: 'test.ts', isDirectory: () => false } as any
    ]);
    vi.mocked(fs.default.readFile).mockResolvedValue('test content');
    vi.mocked(fs.default.mkdir).mockResolvedValue(undefined);
    vi.mocked(fs.default.writeFile).mockResolvedValue(undefined);
    
    // Mock API calls
    vi.mocked(claude.uploadFileToProject).mockResolvedValue(undefined);
    vi.mocked(claude.downloadFilesFromProject).mockResolvedValue(mockFiles);

    await syncFiles('test-project'); // Should default to 'both'

    // Verify both upload and download were called
    expect(claude.uploadFileToProject).toHaveBeenCalled();
    expect(claude.downloadFilesFromProject).toHaveBeenCalledWith(mockProjectConfig.projectId);
    expect(configure.updateLastSynced).toHaveBeenCalledWith('test-project');
  });

  it('should handle upload errors gracefully', async () => {
    // Mock project config
    vi.mocked(configure.getProjectConfig).mockReturnValue(mockProjectConfig);
    vi.mocked(configure.updateLastSynced).mockImplementation(() => {});
    
    // Mock file system
    const fs = await import('fs/promises');
    vi.mocked(fs.default.readdir).mockResolvedValue([
      { name: 'test.ts', isDirectory: () => false } as any
    ]);
    vi.mocked(fs.default.readFile).mockResolvedValue('test content');
    
    // Mock API call to throw error
    vi.mocked(claude.uploadFileToProject).mockRejectedValue(new Error('Upload failed'));
    vi.mocked(claude.downloadFilesFromProject).mockResolvedValue([]);

    // Should throw the error now (changed behavior)
    await expect(syncFiles('test-project', 'upload')).rejects.toThrow('Upload failed');
    
    expect(console.error).toHaveBeenCalledWith(
      expect.stringContaining('Synchronization failed'),
      expect.any(Error)
    );
  });

  it('should handle download errors gracefully', async () => {
    // Mock project config
    vi.mocked(configure.getProjectConfig).mockReturnValue(mockProjectConfig);
    vi.mocked(configure.updateLastSynced).mockImplementation(() => {});
    
    // Mock API call to throw error
    vi.mocked(claude.downloadFilesFromProject).mockRejectedValue(new Error('Download failed'));

    // Should throw the error now (changed behavior)
    await expect(syncFiles('test-project', 'download')).rejects.toThrow('Download failed');
    
    expect(console.error).toHaveBeenCalledWith(
      expect.stringContaining('Synchronization failed'),
      expect.any(Error)
    );
  });
});