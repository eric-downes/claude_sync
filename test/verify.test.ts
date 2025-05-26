import { describe, it, expect } from 'vitest';

describe('ESM Test Verification', () => {
  it('basic test works', () => {
    expect(true).toBe(true);
  });

  it('can access globals', () => {
    // Test access to global mock functions
    global.consoleMock.log('test');
    expect(global.consoleMock.log).toHaveBeenCalledWith('test');
  });

  it('can create mock project', () => {
    const project = global.createMockProject('test-id', 'Test Project');
    expect(project.id).toBe('test-id');
    expect(project.name).toBe('Test Project');
    expect(project.knowledgeBase).toBeDefined();
  });
});