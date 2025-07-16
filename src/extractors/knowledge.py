"""
Extractor for project knowledge files from Claude.ai projects.
"""
import time
from typing import List, Dict, Any, Optional
import logging

from src.chrome.client import ChromeClient
from src.chrome.exceptions import ChromeWebSocketError, ExtractionError
from src.extractors.models import Project, KnowledgeFile

logger = logging.getLogger(__name__)


class ProjectKnowledgeExtractor:
    """Extracts knowledge files from a specific Claude.ai project."""
    
    def __init__(self, client: ChromeClient):
        """Initialize the knowledge extractor with a Chrome client."""
        self.client = client
    
    def navigate_to_project(self, project: Project) -> None:
        """Navigate to a specific project page."""
        logger.info(f"Navigating to project: {project.name}")
        self.client.send_command("Page.navigate", {"url": project.url})
        time.sleep(2)  # Wait for page load
    
    def _wait_for_knowledge_section_loaded(self, timeout: int = 30) -> None:
        """Wait for the knowledge section to be loaded on the page."""
        start_time = time.time()
        
        while True:
            if time.time() - start_time > timeout:
                raise ExtractionError(f"Timeout waiting for knowledge section after {timeout} seconds")
            
            try:
                # Check if knowledge section is present and loaded
                result = self.client.send_command("Runtime.evaluate", {
                    "expression": """
                        (() => {
                            // Look for knowledge section indicators
                            const knowledgeSection = document.querySelector('[data-testid="knowledge-section"], .knowledge-section, section[aria-label*="knowledge" i]');
                            const hasKnowledgeFiles = document.querySelector('[data-testid="knowledge-file"], .knowledge-file, [aria-label*="knowledge file" i]');
                            const hasKnowledgeHeader = Array.from(document.querySelectorAll('h2, h3')).some(h => 
                                h.textContent.toLowerCase().includes('knowledge') || 
                                h.textContent.toLowerCase().includes('project files')
                            );
                            
                            return !!(knowledgeSection || hasKnowledgeFiles || hasKnowledgeHeader);
                        })()
                    """
                })
                
                if result.get("result", {}).get("value", False):
                    logger.info("Knowledge section loaded")
                    return
                    
            except Exception as e:
                logger.debug(f"Error checking knowledge section: {e}")
            
            time.sleep(0.5)
    
    def _extract_knowledge_files(self) -> List[Dict[str, Any]]:
        """Extract list of knowledge files from the current project page."""
        try:
            result = self.client.send_command("Runtime.evaluate", {
                "expression": """
                    (() => {
                        const files = [];
                        
                        // Try multiple selectors to find knowledge files
                        const fileElements = document.querySelectorAll(
                            '[data-testid="knowledge-file"], ' +
                            '.knowledge-file, ' +
                            '[aria-label*="knowledge file" i], ' +
                            '.file-item, ' +
                            '[role="listitem"][aria-label*="file" i]'
                        );
                        
                        fileElements.forEach((element, index) => {
                            // Extract file name
                            const nameElement = element.querySelector('.file-name, [data-testid="file-name"], h4, strong');
                            const name = nameElement ? nameElement.textContent.trim() : 
                                         element.textContent.trim().split('\\n')[0];
                            
                            if (!name) return;
                            
                            // Extract file type from extension or class
                            const extension = name.split('.').pop().toLowerCase();
                            const typeMap = {
                                'md': 'markdown',
                                'py': 'python',
                                'js': 'javascript',
                                'ts': 'typescript',
                                'json': 'json',
                                'yaml': 'yaml',
                                'yml': 'yaml',
                                'txt': 'text',
                                'html': 'html',
                                'css': 'css'
                            };
                            
                            files.push({
                                name: name,
                                type: typeMap[extension] || extension || 'text',
                                size: null,  // Size not always available
                                element_id: element.id || `knowledge-file-${index}`
                            });
                        });
                        
                        return files;
                    })()
                """
            })
            
            return result.get("result", {}).get("value", [])
            
        except Exception as e:
            logger.error(f"Failed to extract knowledge files: {e}")
            return []
    
    def _download_file_content(self, element_id: str, file_name: str) -> str:
        """Download the content of a specific knowledge file."""
        logger.info(f"Downloading content for file: {file_name}")
        
        # Click on the file to open it
        self.client.send_command("Runtime.evaluate", {
            "expression": f"""
                (() => {{
                    const element = document.getElementById('{element_id}') || 
                                   document.querySelector('[data-testid="knowledge-file"]');
                    if (element) {{
                        element.click();
                        return true;
                    }}
                    return false;
                }})()
            """
        })
        
        # Wait for content to load
        time.sleep(1)
        self._wait_for_file_content_loaded()
        
        # Extract the file content
        result = self.client.send_command("Runtime.evaluate", {
            "expression": """
                (() => {
                    // Try multiple selectors for file content
                    const contentElement = document.querySelector(
                        '[data-testid="file-content"], ' +
                        '.file-content, ' +
                        '.code-content, ' +
                        'pre, ' +
                        '.markdown-content, ' +
                        '[role="document"]'
                    );
                    
                    if (contentElement) {
                        return contentElement.textContent || contentElement.innerText || '';
                    }
                    
                    // Fallback: look for any large text block
                    const textBlocks = Array.from(document.querySelectorAll('div, section'))
                        .filter(el => el.textContent.length > 100)
                        .sort((a, b) => b.textContent.length - a.textContent.length);
                    
                    if (textBlocks.length > 0) {
                        return textBlocks[0].textContent;
                    }
                    
                    return '';
                })()
            """
        })
        
        return result.get("result", {}).get("value", "")
    
    def _wait_for_file_content_loaded(self, timeout: int = 10) -> None:
        """Wait for file content to be loaded after clicking on a file."""
        start_time = time.time()
        
        while True:
            if time.time() - start_time > timeout:
                logger.warning(f"Timeout waiting for file content after {timeout} seconds")
                return
            
            try:
                result = self.client.send_command("Runtime.evaluate", {
                    "expression": """
                        (() => {
                            const hasContent = document.querySelector(
                                '[data-testid="file-content"], ' +
                                '.file-content, ' +
                                '.code-content, ' +
                                'pre, ' +
                                '.markdown-content'
                            );
                            return !!hasContent;
                        })()
                    """
                })
                
                if result.get("result", {}).get("value", False):
                    return
                    
            except Exception:
                pass
            
            time.sleep(0.5)
    
    def extract_project_knowledge(self, project: Project, retry_count: int = 3) -> List[KnowledgeFile]:
        """
        Extract all knowledge files from a project.
        
        Args:
            project: The project to extract knowledge from
            retry_count: Number of retries for failed operations
            
        Returns:
            List of KnowledgeFile objects with content
        """
        knowledge_files = []
        
        for attempt in range(retry_count):
            try:
                # Navigate to the project
                self.navigate_to_project(project)
                
                # Wait for knowledge section to load
                self._wait_for_knowledge_section_loaded()
                
                # Extract list of files
                file_list = self._extract_knowledge_files()
                
                if not file_list:
                    logger.info(f"No knowledge files found in project: {project.name}")
                    return []
                
                # Download content for each file
                for file_info in file_list:
                    try:
                        content = self._download_file_content(
                            file_info["element_id"],
                            file_info["name"]
                        )
                        
                        knowledge_file = KnowledgeFile(
                            name=file_info["name"],
                            content=content,
                            file_type=file_info["type"],
                            size=len(content) if content else 0
                        )
                        
                        knowledge_files.append(knowledge_file)
                        logger.info(f"Successfully extracted: {file_info['name']}")
                        
                    except Exception as e:
                        logger.error(f"Failed to download {file_info['name']}: {e}")
                        continue
                
                return knowledge_files
                
            except ChromeWebSocketError as e:
                logger.warning(f"Chrome connection error on attempt {attempt + 1}: {e}")
                if attempt < retry_count - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                raise
                
            except Exception as e:
                logger.error(f"Failed to extract project knowledge on attempt {attempt + 1}: {e}")
                if attempt < retry_count - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise
        
        return knowledge_files