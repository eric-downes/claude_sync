// Main exports for claude-sync
export { configureProject, getProjectConfig, getAllProjects, addProjectConfig } from './config/configure.js';
export { syncFiles } from './sync/sync.js';
export { syncAllProjects } from './sync/sync-all.js';
export { watchProject } from './sync/watcher.js';
export { startMCPServer } from './mcp/server.js';
export { uploadFileToProject, downloadFilesFromProject, listAllProjects } from './api/claude.js';

// Types
export type { ClaudeProject, ClaudeProjectWithKnowledge, ClaudeKnowledgeFile, ClaudeUser, ClaudeAPIClient } from './api/interfaces.js';