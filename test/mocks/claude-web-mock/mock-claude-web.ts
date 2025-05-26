/**
 * Mock Claude.ai web interface for testing browser automation
 */
import { EventEmitter } from 'events';

// Types for mock web interface
interface MockWebProject {
  id: string;
  name: string;
  description: string;
  files: MockWebFile[];
  createdAt: Date;
  updatedAt: Date;
}

interface MockWebFile {
  id: string;
  name: string;
  content: string;
  createdAt: Date;
  updatedAt: Date;
}

interface MockSession {
  isAuthenticated: boolean;
  userEmail: string;
  authToken: string;
}

// Mock browser automation for Claude.ai
export class MockClaudeWeb extends EventEmitter {
  private projects: Map<string, MockWebProject>;
  private session: MockSession;
  private currentPage: string;
  
  constructor() {
    super();
    this.projects = new Map();
    this.session = {
      isAuthenticated: false,
      userEmail: '',
      authToken: ''
    };
    this.currentPage = '/';
    
    // Add some mock projects
    this.addMockProject('Project 1', 'My first Claude project');
    this.addMockProject('Research Notes', 'Research and notes on AI topics');
  }
  
  /**
   * Create a mock project
   */
  private addMockProject(name: string, description: string): string {
    const id = `proj_${Math.random().toString(36).substring(2, 10)}`;
    const now = new Date();
    
    const project: MockWebProject = {
      id,
      name,
      description,
      files: [],
      createdAt: now,
      updatedAt: now
    };
    
    this.projects.set(id, project);
    return id;
  }
  
  /**
   * Simulate login
   */
  async login(email: string, password: string): Promise<boolean> {
    // Simulate network delay
    await new Promise(resolve => setTimeout(resolve, 500));
    
    if (password === 'test-password') {
      this.session = {
        isAuthenticated: true,
        userEmail: email,
        authToken: `token_${Math.random().toString(36).substring(2, 10)}`
      };
      this.currentPage = '/home';
      return true;
    }
    
    return false;
  }
  
  /**
   * Navigate to a page
   */
  async navigateTo(url: string): Promise<string> {
    // Simulate network delay
    await new Promise(resolve => setTimeout(resolve, 300));
    
    // Require authentication for most pages
    if (url !== '/' && url !== '/login' && !this.session.isAuthenticated) {
      this.currentPage = '/login';
      return 'Redirected to login page';
    }
    
    this.currentPage = url;
    
    // Get page content
    if (url === '/projects') {
      return this.renderProjectsPage();
    } else if (url.startsWith('/projects/') && url.includes('/edit')) {
      const projectId = url.split('/')[2];
      return this.renderProjectEditPage(projectId);
    } else if (url.startsWith('/projects/')) {
      const projectId = url.split('/')[2];
      return this.renderProjectPage(projectId);
    } else if (url === '/home') {
      return this.renderHomePage();
    } else if (url === '/login') {
      return this.renderLoginPage();
    }
    
    return 'Page not found';
  }
  
  /**
   * Render login page
   */
  private renderLoginPage(): string {
    return `
      <html>
        <head><title>Claude - Login</title></head>
        <body>
          <div class="login-container">
            <h1>Log in to Claude</h1>
            <form id="login-form">
              <input type="email" name="email" placeholder="Email" />
              <input type="password" name="password" placeholder="Password" />
              <button type="submit">Log in</button>
            </form>
          </div>
        </body>
      </html>
    `;
  }
  
  /**
   * Render home page
   */
  private renderHomePage(): string {
    return `
      <html>
        <head><title>Claude - Home</title></head>
        <body>
          <nav>
            <a href="/home">Home</a>
            <a href="/projects">Projects</a>
          </nav>
          <div class="welcome">
            <h1>Welcome to Claude, ${this.session.userEmail}</h1>
          </div>
        </body>
      </html>
    `;
  }
  
  /**
   * Render projects page
   */
  private renderProjectsPage(): string {
    const projectsHtml = Array.from(this.projects.values())
      .map(project => `
        <div class="project-card" data-project-id="${project.id}">
          <h2><a href="/projects/${project.id}">${project.name}</a></h2>
          <p>${project.description}</p>
          <span>Last updated: ${project.updatedAt.toISOString()}</span>
        </div>
      `)
      .join('');
    
    return `
      <html>
        <head><title>Claude - Projects</title></head>
        <body>
          <nav>
            <a href="/home">Home</a>
            <a href="/projects">Projects</a>
          </nav>
          <div class="projects-container">
            <h1>Your Projects</h1>
            <div class="projects-list">
              ${projectsHtml}
            </div>
            <button id="create-project">Create New Project</button>
          </div>
        </body>
      </html>
    `;
  }
  
  /**
   * Render project page
   */
  private renderProjectPage(projectId: string): string {
    const project = this.projects.get(projectId);
    if (!project) {
      return 'Project not found';
    }
    
    const filesHtml = project.files
      .map(file => `
        <div class="file-item" data-file-id="${file.id}">
          <span class="file-name">${file.name}</span>
          <span class="file-date">${file.updatedAt.toISOString()}</span>
          <button class="file-edit" data-file-id="${file.id}">Edit</button>
          <button class="file-delete" data-file-id="${file.id}">Delete</button>
        </div>
      `)
      .join('');
    
    return `
      <html>
        <head><title>Claude - ${project.name}</title></head>
        <body>
          <nav>
            <a href="/home">Home</a>
            <a href="/projects">Projects</a>
          </nav>
          <div class="project-container">
            <h1>${project.name}</h1>
            <p>${project.description}</p>
            
            <div class="project-actions">
              <a href="/projects/${projectId}/edit">Edit Project</a>
              <button id="upload-file">Upload File</button>
            </div>
            
            <div class="files-container">
              <h2>Files</h2>
              <div class="files-list">
                ${filesHtml}
              </div>
            </div>
          </div>
        </body>
      </html>
    `;
  }
  
  /**
   * Render project edit page
   */
  private renderProjectEditPage(projectId: string): string {
    const project = this.projects.get(projectId);
    if (!project) {
      return 'Project not found';
    }
    
    return `
      <html>
        <head><title>Claude - Edit ${project.name}</title></head>
        <body>
          <nav>
            <a href="/home">Home</a>
            <a href="/projects">Projects</a>
          </nav>
          <div class="project-edit-container">
            <h1>Edit Project</h1>
            <form id="project-edit-form">
              <input type="text" name="name" value="${project.name}" />
              <textarea name="description">${project.description}</textarea>
              <button type="submit">Save Changes</button>
            </form>
          </div>
        </body>
      </html>
    `;
  }
  
  /**
   * Upload a file to a project
   */
  async uploadFile(projectId: string, fileName: string, content: string): Promise<MockWebFile | null> {
    // Simulate network delay
    await new Promise(resolve => setTimeout(resolve, 700));
    
    const project = this.projects.get(projectId);
    if (!project) {
      return null;
    }
    
    const fileId = `file_${Math.random().toString(36).substring(2, 10)}`;
    const now = new Date();
    
    const file: MockWebFile = {
      id: fileId,
      name: fileName,
      content,
      createdAt: now,
      updatedAt: now
    };
    
    project.files.push(file);
    project.updatedAt = now;
    
    return file;
  }
  
  /**
   * Get file content
   */
  async getFileContent(projectId: string, fileId: string): Promise<string | null> {
    // Simulate network delay
    await new Promise(resolve => setTimeout(resolve, 400));
    
    const project = this.projects.get(projectId);
    if (!project) {
      return null;
    }
    
    const file = project.files.find(f => f.id === fileId);
    if (!file) {
      return null;
    }
    
    return file.content;
  }
  
  /**
   * Delete a file
   */
  async deleteFile(projectId: string, fileId: string): Promise<boolean> {
    // Simulate network delay
    await new Promise(resolve => setTimeout(resolve, 500));
    
    const project = this.projects.get(projectId);
    if (!project) {
      return false;
    }
    
    const fileIndex = project.files.findIndex(f => f.id === fileId);
    if (fileIndex === -1) {
      return false;
    }
    
    project.files.splice(fileIndex, 1);
    project.updatedAt = new Date();
    
    return true;
  }
  
  /**
   * Get current page
   */
  getCurrentPage(): string {
    return this.currentPage;
  }
  
  /**
   * Get projects
   */
  getProjects(): MockWebProject[] {
    return Array.from(this.projects.values());
  }
  
  /**
   * Close browser
   */
  async close(): Promise<void> {
    // Clean up resources
    this.session.isAuthenticated = false;
    this.currentPage = '/';
    this.emit('close');
  }
}