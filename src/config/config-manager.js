/**
 * Configuration manager for Claude Sync
 * This is a placeholder file for testing purposes
 */

import path from 'path';
import os from 'os';

// Default configuration
const DEFAULT_CONFIG = {
  projectsDir: path.join(os.homedir(), 'claude-sync-projects'),
  apiKey: '',
  syncInterval: 300,
  logLevel: 'info'
};

// In-memory config for testing
let config = { ...DEFAULT_CONFIG };

/**
 * Load configuration
 */
export function loadConfig() {
  return { ...config };
}

/**
 * Save configuration
 */
export function saveConfig(newConfig) {
  config = { ...config, ...newConfig };
  return config;
}

/**
 * Get a configuration value
 */
export function getConfigValue(key) {
  return config[key];
}

/**
 * Set a configuration value
 */
export function setConfigValue(key, value) {
  config[key] = value;
  return config;
}

/**
 * Reset configuration to defaults
 */
export function resetConfig() {
  config = { ...DEFAULT_CONFIG };
  return config;
}