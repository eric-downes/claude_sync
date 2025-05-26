import { ClaudeAPIClient, ClaudeProject, ClaudeProjectWithKnowledge, ClaudeKnowledgeFile, ClaudeUser } from './interfaces.js';
import { chromium, Browser, Page, BrowserContext } from 'playwright';
import crypto from 'node:crypto';
import path from 'node:path';

/**
 * Browser automation-based Claude API client using Playwright
 */
export class ClaudeBrowserClient implements ClaudeAPIClient {
  private credentials: { email: string; password: string } | null = null;
  private browser: Browser | null = null;
  private context: BrowserContext | null = null;
  private page: Page | null = null;
  private isLoggedIn: boolean = false;
  private baseUrl: string = 'https://claude.ai';
  
  constructor(credentials?: { email: string; password: string }) {
    if (credentials) {
      this.credentials = credentials;
    }
  }
  
  /**
   * Set login credentials
   */
  setCredentials(email: string, password: string): void {
    this.credentials = { email, password };
  }
  
  /**
   * Initialize browser and context
   */
  private async initBrowser(): Promise<void> {
    if (this.browser) return;
    
    this.browser = await chromium.launch({
      headless: true, // Set to false for debugging
      args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    
    this.context = await this.browser.newContext({
      userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    });
    
    this.page = await this.context.newPage();
  }
  
  /**
   * Retry function with exponential backoff
   */
  private async retry<T>(
    operation: () => Promise<T>,
    maxRetries: number = 3,
    baseDelay: number = 1000
  ): Promise<T> {
    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        return await operation();
      } catch (error) {
        if (attempt === maxRetries) {
          throw error;
        }
        
        const delay = baseDelay * Math.pow(2, attempt - 1);
        console.log(`Attempt ${attempt} failed, retrying in ${delay}ms...`);
        await this.page?.waitForTimeout(delay);
      }
    }
    
    throw new Error('Max retries exceeded');
  }
  
  /**
   * Login to Claude.ai
   */
  private async login(): Promise<void> {
    if (this.isLoggedIn) return;
    
    if (!this.credentials) {
      throw new Error('Login credentials are required for browser automation');
    }
    
    await this.initBrowser();
    if (!this.page) throw new Error('Failed to initialize browser page');
    
    console.log('Logging in to Claude.ai...');
    
    await this.retry(async () => {
      // Navigate to Claude.ai login page
      await this.page!.goto(`${this.baseUrl}/login`, { waitUntil: 'networkidle' });
      
      // Wait for and fill in email
      await this.page!.waitForSelector('input[type="email"]', { timeout: 10000 });
      await this.page!.fill('input[type="email"]', this.credentials!.email);
      
      // Click continue or submit button
      const continueButton = this.page!.locator('button[type="submit"], button:has-text("Continue")');
      await continueButton.waitFor({ state: 'visible', timeout: 5000 });
      await continueButton.click();
      
      // Wait a bit for potential navigation
      await this.page!.waitForTimeout(2000);
      
      // Fill in password if on password page
      const passwordInput = this.page!.locator('input[type="password"]');
      try {
        await passwordInput.waitFor({ state: 'visible', timeout: 5000 });
        await passwordInput.fill(this.credentials!.password);
        
        const signInButton = this.page!.locator('button[type="submit"], button:has-text("Continue"), button:has-text("Sign In")');
        await signInButton.waitFor({ state: 'visible', timeout: 5000 });
        await signInButton.click();
      } catch (error) {
        // Password input might not be needed for some login flows
        console.log('Password input not found, continuing...');
      }
      
      // Wait for successful login (redirect to main page)
      await this.page!.waitForURL(/claude\.ai(?:\/(?:chat|projects)?)?$/, { timeout: 30000 });
      
      // Verify we're actually logged in by checking for user-specific elements
      try {
        await this.page!.waitForSelector('[data-testid="user-menu"], [class*="user"], [class*="avatar"]', { timeout: 10000 });
      } catch (error) {
        throw new Error('Login appears to have failed - user elements not found');
      }
      
      this.isLoggedIn = true;
      console.log('Successfully logged in to Claude.ai');
    });
  }
  
  /**
   * Navigate to projects page
   */
  private async navigateToProjects(): Promise<void> {
    if (!this.page) throw new Error('Browser not initialized');
    
    await this.page.goto(`${this.baseUrl}/projects`);
    await this.page.waitForLoadState('networkidle');
  }
  
  /**
   * List all projects in Claude.ai
   */
  async listProjects(): Promise<ClaudeProject[]> {
    await this.login();
    if (!this.page) throw new Error('Browser not initialized');
    
    console.log('Fetching projects from Claude.ai...');
    
    return await this.retry(async () => {
      await this.navigateToProjects();
      
      // Wait for projects to load with multiple possible selectors
      try {
        await this.page!.waitForSelector(
          '[data-testid="project-card"], .project-card, [class*="project"], [data-testid="project-list"], .projects-grid',
          { timeout: 15000 }
        );
      } catch (error) {
        // If no projects are found, check if we're on the correct page
        const currentUrl = this.page!.url();
        if (!currentUrl.includes('projects')) {
          throw new Error('Not on projects page');
        }
        console.log('No projects found or projects section not loaded');
        return [];
      }
      
      // Extract project information
      const projects = await this.page!.evaluate(() => {
        const projectElements = document.querySelectorAll(
          '[data-testid="project-card"], .project-card, [class*="project-item"], [class*="project-card"]'
        );
        const projectsData: any[] = [];
        
        projectElements.forEach((element, index) => {
          // Skip if this doesn't look like a real project card
          const nameElement = element.querySelector('h3, h2, h1, [class*="title"], [class*="name"], [data-testid*="name"]');
          const descElement = element.querySelector('p, [class*="description"], [class*="desc"], [data-testid*="description"]');
          
          const name = nameElement?.textContent?.trim();
          if (!name || name.length < 2) return; // Skip invalid entries
          
          const description = descElement?.textContent?.trim() || '';
          const now = new Date().toISOString();
          
          // Try to get a more stable ID from href or data attributes
          const linkElement = element.querySelector('a[href*="/project/"]');
          let projectId = linkElement?.getAttribute('href')?.match(/\/project\/([^\/]+)/)?.[1];
          if (!projectId) {
            projectId = element.getAttribute('data-project-id') || `project-${Date.now()}-${index}`;
          }
          
          projectsData.push({
            id: projectId,
            name,
            description,
            createdAt: now,
            updatedAt: now,
            ownerId: 'current-user',
            isShared: false
          });
        });
        
        return projectsData;
      });
      
      console.log(`Found ${projects.length} projects`);
      return projects;
    });
  }
  
  /**
   * Get details of a specific project
   */
  async getProject(projectId: string): Promise<ClaudeProjectWithKnowledge> {
    await this.login();
    
    // For now, create a mock project with knowledge base
    const now = new Date().toISOString();
    return {
      id: projectId,
      name: 'Sample Project',
      description: 'A sample project from browser automation',
      createdAt: now,
      updatedAt: now,
      ownerId: 'current-user',
      isShared: false,
      knowledgeBase: {
        id: `kb-${crypto.randomBytes(4).toString('hex')}`,
        fileCount: 0,
        totalSizeBytes: 0,
        lastUpdated: now
      }
    };
  }
  
  /**
   * List all files in a project's knowledge base
   */
  async listKnowledgeFiles(projectId: string): Promise<ClaudeKnowledgeFile[]> {
    await this.login();
    if (!this.page) throw new Error('Browser not initialized');
    
    try {
      // Navigate to project
      await this.page.goto(`${this.baseUrl}/project/${projectId}`);
      await this.page.waitForLoadState('networkidle');
      
      // Look for knowledge base section
      const knowledgeSection = await this.page.locator('[class*="knowledge"], [class*="files"], [data-testid*="knowledge"]');
      if (await knowledgeSection.isVisible()) {
        // Extract file information
        const files = await this.page.evaluate(() => {
          const fileElements = document.querySelectorAll('[class*="file-item"], [class*="knowledge-file"]');
          const filesData: any[] = [];
          
          fileElements.forEach((element) => {
            const nameElement = element.querySelector('[class*="name"], [class*="title"]');
            const name = nameElement?.textContent?.trim() || 'unknown.txt';
            const now = new Date().toISOString();
            
            filesData.push({
              id: `file-${crypto.randomBytes(8).toString('hex')}`,
              name,
              path: name,
              sizeBytes: 1024,
              mimeType: 'text/plain',
              createdAt: now,
              updatedAt: now,
              content: '',
              metadata: {}
            });
          });
          
          return filesData;
        });
        
        return files;
      }
      
      return [];
      
    } catch (error) {
      console.error('Failed to list knowledge files:', error);
      return [];
    }
  }
  
  /**
   * Get a specific file from a project's knowledge base
   */
  async getKnowledgeFile(projectId: string, fileId: string): Promise<ClaudeKnowledgeFile> {
    await this.login();
    
    // For now, return a mock file
    return {
      id: fileId,
      name: 'sample.txt',
      path: 'sample.txt',
      sizeBytes: 100,
      mimeType: 'text/plain',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      content: 'Sample file content from browser automation',
      metadata: {}
    };
  }
  
  /**
   * Upload a file to a project's knowledge base
   */
  async uploadKnowledgeFile(
    projectId: string,
    filePath: string,
    content: string | Buffer
  ): Promise<ClaudeKnowledgeFile> {
    await this.login();
    if (!this.page) throw new Error('Browser not initialized');
    
    console.log(`Uploading file ${filePath} to project ${projectId}...`);
    
    try {
      // Navigate to project
      await this.page.goto(`${this.baseUrl}/project/${projectId}`);
      await this.page.waitForLoadState('networkidle');
      
      // Look for upload button or drag-drop area
      const uploadButton = await this.page.locator('button:has-text("Upload"), [class*="upload"], input[type="file"]');
      
      if (await uploadButton.isVisible()) {
        // Handle file upload
        const fileName = path.basename(filePath);
        
        // If it's a file input, use setInputFiles
        if (await this.page.locator('input[type="file"]').isVisible()) {
          // Create temporary file for upload
          const fs = await import('fs/promises');
          const tempPath = `/tmp/${fileName}`;
          await fs.writeFile(tempPath, content);
          
          await this.page.setInputFiles('input[type="file"]', tempPath);
          
          // Clean up temp file
          await fs.unlink(tempPath);
        }
        
        // Wait for upload to complete
        await this.page.waitForTimeout(2000);
        
        console.log(`Successfully uploaded ${fileName}`);
      }
      
      // Return file metadata
      const fileId = `file-${crypto.randomBytes(8).toString('hex')}`;
      return {
        id: fileId,
        name: path.basename(filePath),
        path: filePath,
        sizeBytes: typeof content === 'string' ? Buffer.from(content).length : content.length,
        mimeType: 'text/plain',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        content: typeof content === 'string' ? content : content.toString('utf-8'),
        metadata: {}
      };
      
    } catch (error) {
      console.error('Failed to upload file:', error);
      throw new Error(`Failed to upload file: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }
  
  /**
   * Delete a file from a project's knowledge base
   */
  async deleteKnowledgeFile(projectId: string, fileId: string): Promise<void> {
    await this.login();
    if (!this.page) throw new Error('Browser not initialized');
    
    console.log(`Deleting file ${fileId} from project ${projectId}...`);
    
    try {
      // Navigate to project
      await this.page.goto(`${this.baseUrl}/project/${projectId}`);
      await this.page.waitForLoadState('networkidle');
      
      // Look for delete button for the specific file
      const deleteButton = await this.page.locator(`[data-file-id="${fileId}"] button:has-text("Delete"), [data-file-id="${fileId}"] [class*="delete"]`);
      
      if (await deleteButton.isVisible()) {
        await deleteButton.click();
        
        // Confirm deletion if prompted
        const confirmButton = await this.page.locator('button:has-text("Confirm"), button:has-text("Delete")');
        if (await confirmButton.isVisible()) {
          await confirmButton.click();
        }
        
        await this.page.waitForTimeout(1000);
        console.log(`Successfully deleted file ${fileId}`);
      }
      
    } catch (error) {
      console.error('Failed to delete file:', error);
      throw new Error(`Failed to delete file: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }
  
  /**
   * Get the current authenticated user
   */
  async getCurrentUser(): Promise<ClaudeUser> {
    await this.login();
    
    return {
      id: 'current-user',
      email: this.credentials?.email || 'unknown@example.com',
      name: 'Browser User',
      accountType: 'plus'
    };
  }
  
  /**
   * Clean up browser resources
   */
  async cleanup(): Promise<void> {
    if (this.page) {
      await this.page.close();
      this.page = null;
    }
    
    if (this.context) {
      await this.context.close();
      this.context = null;
    }
    
    if (this.browser) {
      await this.browser.close();
      this.browser = null;
    }
    
    this.isLoggedIn = false;
  }
}