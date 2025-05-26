import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { syncFiles } from '../sync/sync.js';
import * as configure from '../config/configure.js';
import * as claude from '../api/claude.js';

// Mock the dependencies
vi.mock('../config/configure.js');
vi.mock('../api/claude.js');
vi.mock('fs/promises', () => ({
  readdir: vi.fn(),
  readFile: vi.fn(),
  writeFile: vi.fn(),
  mkdir: vi.fn(),
}));

describe('Sync Module', () => {
  const mockProjectConfig = {
    projectId: 'test-project-123',
    localPath: '/mock/project/path',
    excludePatterns: ['node_modules/**', '.git/**']
  };

  const mockFiles = [
    { id: 'file1', name: 'src/main.ts', content: 'console.log("test");' },
    { id: 'file2', name: 'README.md', content: '# Test Project' }
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
    vi.mocked(fs.readdir).mockResolvedValue([
      { name: 'src', isDirectory: () => true } as any,
      { name: 'README.md', isDirectory: () => false } as any
    ]);
    vi.mocked(fs.readFile).mockResolvedValue('file content');
    
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
    vi.mocked(fs.mkdir).mockResolvedValue(undefined);
    vi.mocked(fs.writeFile).mockResolvedValue(undefined);

    await syncFiles('test-project', 'download');

    // Verify download was called but upload was not
    expect(claude.downloadFilesFromProject).toHaveBeenCalledWith(mockProjectConfig.projectId);
    expect(claude.uploadFileToProject).not.toHaveBeenCalled();
    expect(fs.writeFile).toHaveBeenCalledTimes(2); // Two mock files
    expect(configure.updateLastSynced).toHaveBeenCalledWith('test-project');
  });
  
  it('should sync in both directions by default', async () => {
    // Mock project config
    vi.mocked(configure.getProjectConfig).mockReturnValue(mockProjectConfig);
    vi.mocked(configure.updateLastSynced).mockImplementation(() => {});
    
    // Mock file system for upload
    const fs = await import('fs/promises');
    vi.mocked(fs.readdir).mockResolvedValue([
      { name: 'test.ts', isDirectory: () => false } as any
    ]);
    vi.mocked(fs.readFile).mockResolvedValue('test content');
    vi.mocked(fs.mkdir).mockResolvedValue(undefined);
    vi.mocked(fs.writeFile).mockResolvedValue(undefined);
    
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
    vi.mocked(fs.readdir).mockResolvedValue([
      { name: 'test.ts', isDirectory: () => false } as any
    ]);
    vi.mocked(fs.readFile).mockResolvedValue('test content');
    
    // Mock API call to throw error
    vi.mocked(claude.uploadFileToProject).mockRejectedValue(new Error('Upload failed'));
    vi.mocked(claude.downloadFilesFromProject).mockResolvedValue([]);

    // Should not throw, but handle error gracefully
    await expect(syncFiles('test-project', 'upload')).resolves.not.toThrow();
    
    expect(console.error).toHaveBeenCalledWith(
      expect.stringContaining('Failed to upload'),
      expect.any(Error)
    );
  });

  it('should handle download errors gracefully', async () => {
    // Mock project config
    vi.mocked(configure.getProjectConfig).mockReturnValue(mockProjectConfig);
    vi.mocked(configure.updateLastSynced).mockImplementation(() => {});
    
    // Mock API call to throw error
    vi.mocked(claude.downloadFilesFromProject).mockRejectedValue(new Error('Download failed'));

    // Should not throw, but handle error gracefully
    await expect(syncFiles('test-project', 'download')).resolves.not.toThrow();
    
    expect(console.error).toHaveBeenCalledWith(
      expect.stringContaining('Error during download'),
      expect.any(Error)
    );
  });
});