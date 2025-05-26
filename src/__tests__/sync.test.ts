import { describe, test, expect, jest, beforeEach } from '@jest/globals';
import { syncFiles } from '../sync/sync.js';
import * as configModule from '../config/configure.js';
import * as claudeApi from '../api/claude.js';

// Mock the config module
jest.mock('../config/configure.js', () => ({
  getProjectConfig: jest.fn(),
  updateLastSynced: jest.fn()
}));

// Mock the Claude API module
jest.mock('../api/claude.js', () => ({
  uploadFileToProject: jest.fn(),
  downloadFilesFromProject: jest.fn()
}));

describe('Sync Module', () => {
  beforeEach(() => {
    // Reset mocks
    jest.resetAllMocks();
    
    // Setup default mock responses
    (configModule.getProjectConfig as jest.Mock).mockReturnValue({
      projectId: 'test-project-id',
      projectName: 'Test Project',
      localPath: '/test/path',
      excludePatterns: ['node_modules', '*.log']
    });
    
    (claudeApi.downloadFilesFromProject as jest.Mock).mockResolvedValue([
      {
        name: 'test.txt',
        content: 'test content',
        lastModified: new Date()
      }
    ]);
  });
  
  test('should throw error if project not found', async () => {
    // Setup
    (configModule.getProjectConfig as jest.Mock).mockReturnValue(null);
    
    // Act & Assert
    await expect(async () => {
      await syncFiles('non-existent-project');
    }).rejects.toThrow('Project "non-existent-project" not found');
  });
  
  test('should sync in upload direction only', async () => {
    // Act
    await syncFiles('test-project', 'upload');
    
    // Assert
    expect(claudeApi.uploadFileToProject).toHaveBeenCalled();
    expect(claudeApi.downloadFilesFromProject).not.toHaveBeenCalled();
    expect(configModule.updateLastSynced).toHaveBeenCalledWith('test-project');
  });
  
  test('should sync in download direction only', async () => {
    // Act
    await syncFiles('test-project', 'download');
    
    // Assert
    expect(claudeApi.uploadFileToProject).not.toHaveBeenCalled();
    expect(claudeApi.downloadFilesFromProject).toHaveBeenCalledWith('test-project-id');
    expect(configModule.updateLastSynced).toHaveBeenCalledWith('test-project');
  });
  
  test('should sync in both directions by default', async () => {
    // Act
    await syncFiles('test-project');
    
    // Assert
    expect(claudeApi.uploadFileToProject).toHaveBeenCalled();
    expect(claudeApi.downloadFilesFromProject).toHaveBeenCalledWith('test-project-id');
    expect(configModule.updateLastSynced).toHaveBeenCalledWith('test-project');
  });
});