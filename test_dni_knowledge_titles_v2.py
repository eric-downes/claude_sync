#!/usr/bin/env python3
"""
Simple test script to print knowledge file titles from DNI project.
Version 2 with better debugging.
"""
import logging
import sys
import time
from src.chrome.robust_client import RobustChromeClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main function to extract and print DNI knowledge file titles."""
    logger.info("Starting DNI Project Knowledge File Title Extraction (v2)")
    logger.info("=" * 60)
    
    try:
        # Create Chrome client
        with RobustChromeClient() as client:
            # Get available pages
            pages = client.get_pages()
            claude_page = None
            
            # Find Claude.ai page
            for page in pages:
                if 'claude.ai' in page.get('url', ''):
                    claude_page = page
                    break
            
            if not claude_page:
                logger.error("No Claude.ai page found")
                return 1
            
            # Connect to the page
            logger.info(f"Found Claude page: {claude_page.get('title', 'Untitled')}")
            logger.info(f"URL: {claude_page.get('url', '')}")
            client.connect_to_page(claude_page)
            
            # First, let's check current page state
            current_url = client.evaluate_expression("window.location.href")
            logger.info(f"Current URL: {current_url}")
            
            # Navigate to projects page
            logger.info("Navigating to projects page...")
            client.navigate_and_wait("https://claude.ai/projects")
            time.sleep(3)  # Extra wait
            
            # Check if we're on the projects page
            new_url = client.evaluate_expression("window.location.href")
            logger.info(f"After navigation URL: {new_url}")
            
            # Look for projects using a simpler approach
            logger.info("Looking for projects...")
            
            # Method 1: Find project links directly
            projects_data = client.evaluate_expression("""
                JSON.stringify(
                    Array.from(document.querySelectorAll('a[href*="/project/"]'))
                        .map(link => ({
                            name: link.textContent.trim(),
                            href: link.href,
                            id: link.href.split('/project/')[1] || 'unknown'
                        }))
                )
            """)
            
            if not projects_data:
                logger.warning("No projects found via links, trying alternative method...")
                
                # Method 2: Look for project cards
                projects_data = client.evaluate_expression("""
                    JSON.stringify((() => {
                        const projects = [];
                        // Look for elements containing project info
                        const elements = Array.from(document.querySelectorAll('*'))
                            .filter(el => {
                                const text = el.textContent || '';
                                return text.includes('Updated') && text.includes('ago') && 
                                       !text.includes('Sort by');
                            });
                        
                        elements.forEach(el => {
                            const text = el.textContent.trim();
                            const lines = text.split('\\n').filter(l => l.trim());
                            if (lines.length >= 2) {
                                projects.push({
                                    name: lines[0],
                                    updated: lines.find(l => l.includes('Updated')),
                                    id: 'unknown'
                                });
                            }
                        });
                        
                        return projects;
                    })())
                """)
            
            if not projects_data:
                logger.error("No projects found on the page")
                
                # Debug: print page content snippet
                page_text = client.evaluate_expression("document.body.innerText.substring(0, 500)")
                logger.info(f"Page content preview: {page_text}")
                return 1
            
            logger.info(f"Found {len(projects_data)} projects")
            
            # Find DNI project
            dni_project = None
            for project in projects_data:
                logger.info(f"  - {project.get('name', 'Unknown')}")
                if 'DNI' in project.get('name', '') or 'dni' in project.get('name', '').lower():
                    dni_project = project
                    break
            
            if not dni_project:
                logger.error("DNI project not found!")
                return 1
            
            logger.info(f"\nFound DNI project: {dni_project['name']}")
            
            # Navigate to DNI project
            if dni_project.get('href'):
                logger.info(f"Navigating to: {dni_project['href']}")
                client.navigate_and_wait(dni_project['href'])
            else:
                # Try to click on the project
                logger.info("Clicking on DNI project...")
                click_result = client.evaluate_expression(f"""
                    (() => {{
                        const links = Array.from(document.querySelectorAll('a'));
                        const dniLink = links.find(a => a.textContent.includes('{dni_project['name']}'));
                        if (dniLink) {{
                            dniLink.click();
                            return true;
                        }}
                        return false;
                    }})()
                """)
                if not click_result:
                    logger.error("Failed to click on DNI project")
                    return 1
            
            time.sleep(3)  # Wait for project page to load
            
            # Look for knowledge files
            logger.info("\nLooking for knowledge files...")
            
            # Method 1: Look for file elements with specific patterns
            knowledge_files = client.evaluate_expression("""
                JSON.stringify((() => {
                    const files = [];
                    
                    // Look for elements that contain file information
                    const fileElements = Array.from(document.querySelectorAll('*'))
                        .filter(el => {
                            const text = el.textContent || '';
                            return text.includes('lines') && 
                                   (text.includes('text') || text.includes('.'));
                        });
                    
                    // Extract file names
                    fileElements.forEach(el => {
                        const text = el.textContent.trim();
                        // Look for patterns like "filename.ext • X lines • text"
                        const match = text.match(/^([^•]+)\\s*•\\s*(\\d+\\s*lines)/);
                        if (match) {
                            files.push({
                                name: match[1].trim(),
                                info: text
                            });
                        } else if (text.includes('lines')) {
                            // Try to extract from parent/sibling
                            let fileName = null;
                            if (el.previousElementSibling) {
                                fileName = el.previousElementSibling.textContent.trim();
                            } else if (el.parentElement && el.parentElement.previousElementSibling) {
                                fileName = el.parentElement.previousElementSibling.textContent.trim();
                            }
                            
                            if (fileName && fileName.length < 100 && !fileName.includes('lines')) {
                                files.push({
                                    name: fileName,
                                    info: text
                                });
                            }
                        }
                    });
                    
                    // Deduplicate
                    const unique = {};
                    files.forEach(f => {
                        if (!unique[f.name]) {
                            unique[f.name] = f;
                        }
                    });
                    
                    return Object.values(unique);
                })())
            """)
            
            if not knowledge_files:
                logger.warning("No knowledge files found with first method, trying alternative...")
                
                # Method 2: Look for clickable elements in knowledge section
                knowledge_files = client.evaluate_expression("""
                    JSON.stringify((() => {
                        const files = [];
                        
                        // Find knowledge section
                        const knowledgeSection = Array.from(document.querySelectorAll('*'))
                            .find(el => el.textContent && el.textContent.includes('Project knowledge'));
                        
                        if (knowledgeSection) {
                            // Look for clickable elements within or near the section
                            const parent = knowledgeSection.parentElement;
                            if (parent) {
                                const buttons = parent.querySelectorAll('[role="button"], button, [tabindex="0"]');
                                buttons.forEach(btn => {
                                    const text = btn.textContent.trim();
                                    if (text && !text.includes('Add file') && !text.includes('Project knowledge')) {
                                        files.push({
                                            name: text.split('\\n')[0].trim(),
                                            info: text
                                        });
                                    }
                                });
                            }
                        }
                        
                        return files;
                    })())
                """)
            
            if not knowledge_files:
                logger.warning("No knowledge files found in DNI project")
                
                # Debug: print page content
                page_text = client.evaluate_expression("document.body.innerText.substring(0, 1000)")
                logger.info(f"Page content preview: {page_text}")
                return 0
            
            # Print the titles
            logger.info(f"\nFound {len(knowledge_files)} knowledge files in DNI project:")
            logger.info("-" * 60)
            
            for i, file in enumerate(knowledge_files, 1):
                logger.info(f"{i}. {file['name']}")
                if file.get('info'):
                    logger.info(f"   Info: {file['info']}")
            
            logger.info("-" * 60)
            logger.info("Extraction complete!")
            
            return 0
            
    except Exception as e:
        logger.error(f"Error during extraction: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())