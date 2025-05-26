import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

describe('Vitest Configuration Verification', () => {
  beforeEach(() => {
    // Reset mocks before each test
    vi.resetAllMocks();
  });
  
  afterEach(() => {
    // Clean up after each test
  });
  
  it('should run basic test', () => {
    expect(true).toBe(true);
  });
  
  it('should access global mocks', () => {
    global.consoleMock.log('test message');
    expect(global.consoleMock.log).toHaveBeenCalledWith('test message');
  });
  
  it('should create mock projects', () => {
    const project = global.createMockProject('test-123', 'Test Project');
    expect(project.id).toBe('test-123');
    expect(project.name).toBe('Test Project');
    expect(project.description).toBe('Mock project Test Project');
    expect(project.knowledgeBase.id).toBe('kb_test-123');
  });
  
  it('should mock functions', () => {
    const mockFn = vi.fn();
    mockFn('test');
    expect(mockFn).toHaveBeenCalledOnce();
    expect(mockFn).toHaveBeenCalledWith('test');
  });
  
  it('should mock environment variables', () => {
    expect(process.env.NODE_ENV).toBe('test');
    expect(process.env.CLAUDE_API_KEY).toBe('test-api-key');
  });
});