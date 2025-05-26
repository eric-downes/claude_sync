import Conf from 'conf';
import readline from 'readline';
import { fileURLToPath } from 'url';
import path from 'path';

// Configuration schema
interface ProjectConfig {
  projectId: string;
  projectName: string;
  localPath: string;
  lastSynced?: Date;
  excludePatterns?: string[];
}

interface ClaudeSyncConfig {
  apiKey?: string;
  projects: Record<string, ProjectConfig>;
}

// Initialize configuration
const config = new Conf<ClaudeSyncConfig>({
  projectName: 'claude-sync',
  schema: {
    apiKey: {
      type: 'string',
      default: ''
    },
    projects: {
      type: 'object',
      default: {}
    }
  }
});

// Create readline interface
const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

// Promisify readline question
function question(query: string): Promise<string> {
  return new Promise((resolve) => {
    rl.question(query, (answer) => {
      resolve(answer);
    });
  });
}

// Configure a new project
export async function configureProject(): Promise<void> {
  try {
    // Check if API key exists
    let apiKey = config.get('apiKey');
    if (!apiKey) {
      apiKey = await question('Enter your Claude API key: ');
      config.set('apiKey', apiKey);
      console.log('API key saved.');
    }

    // Get project details
    const projectName = await question('Enter a name for this project: ');
    const projectId = await question('Enter Claude AI project ID (from the URL, e.g., 01965682-47e7-701b-9038-8844669dc224): ');
    const localPath = await question('Enter the local directory path to sync: ');
    const excludePatterns = await question('Enter file patterns to exclude (comma separated, e.g., node_modules,*.log): ');

    // Save project configuration
    const projectConfig: ProjectConfig = {
      projectId,
      projectName,
      localPath,
      excludePatterns: excludePatterns ? excludePatterns.split(',') : undefined
    };

    const projects = config.get('projects');
    projects[projectName] = projectConfig;
    config.set('projects', projects);

    console.log(`Project "${projectName}" configured successfully.`);
  } catch (error) {
    console.error('Error configuring project:', error);
  } finally {
    rl.close();
  }
}

// Get project configuration
export function getProjectConfig(projectName: string): ProjectConfig | null {
  const projects = config.get('projects');
  return projects[projectName] || null;
}

// Get all project configurations
export function getAllProjects(): Record<string, ProjectConfig> {
  return config.get('projects');
}

// Get API key
export function getApiKey(): string | undefined {
  return config.get('apiKey');
}

// Update last synced timestamp
export function updateLastSynced(projectName: string): void {
  const projects = config.get('projects');
  if (projects[projectName]) {
    projects[projectName].lastSynced = new Date();
    config.set('projects', projects);
  }
}

// Add or update a project configuration
export function addProjectConfig(projectName: string, projectConfig: ProjectConfig): void {
  const projects = config.get('projects');
  projects[projectName] = projectConfig;
  config.set('projects', projects);
}