#!/usr/bin/env python3
"""
Extract and display first 5 lines of knowledge files from DLPoS project.
"""
import logging
import time
import json

from src.chrome.robust_client import RobustChromeClient

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def extract_dlpos_knowledge(client):
    """Extract knowledge files from DLPoS project."""
    # Navigate to projects page
    logger.info("Navigating to projects page...")
    client.navigate_and_wait("https://claude.ai/projects")
    
    # Find DLPoS project
    logger.info("Looking for DLPoS project...")
    project_links = client.evaluate_expression("""
        JSON.stringify(
            Array.from(document.querySelectorAll('a[href*="/project/"]'))
                .map(link => ({
                    text: link.innerText || link.textContent || '',
                    href: link.href
                }))
                .filter(p => p.text.includes('DLPoS'))
        )
    """)
    
    if not project_links:
        logger.error("DLPoS project not found")
        return
    
    dlpos_url = project_links[0]['href']
    logger.info(f"Found DLPoS project: {dlpos_url}")
    
    # Navigate to DLPoS project
    logger.info("Navigating to DLPoS project...")
    client.navigate_and_wait(dlpos_url)
    time.sleep(2)  # Extra wait for content to load
    
    # Check if we have knowledge files
    logger.info("Checking for knowledge files...")
    
    # Try multiple approaches to find knowledge files
    
    # Approach 1: Look for file-like elements in the knowledge section
    knowledge_files = client.evaluate_expression("""
        JSON.stringify((() => {
            // Look for elements that might be knowledge files
            const fileElements = [];
            
            // Try to find knowledge section first
            const knowledgeSection = Array.from(document.querySelectorAll('*')).find(el => 
                el.textContent && el.textContent.includes('Project knowledge')
            );
            
            if (knowledgeSection) {
                // Look for file-like elements near the knowledge section
                const parent = knowledgeSection.parentElement;
                if (parent) {
                    // Look for elements that look like files
                    const possibleFiles = parent.querySelectorAll('[role="button"], button, [tabindex="0"]');
                    possibleFiles.forEach(el => {
                        const text = el.textContent || '';
                        // Check if it looks like a filename
                        if (text && (text.includes('.') || text.includes('lines'))) {
                            fileElements.push({
                                text: text.trim(),
                                element: el.tagName,
                                classes: el.className
                            });
                        }
                    });
                }
            }
            
            // Also try to find any text that looks like filenames
            const allText = document.body.innerText;
            const lines = allText.split('\\n');
            const filePatterns = [];
            
            lines.forEach(line => {
                if (line.includes('lines') && (line.includes('text') || line.includes('.'))) {
                    filePatterns.push(line.trim());
                }
            });
            
            return {
                fileElements: fileElements,
                filePatterns: filePatterns.slice(0, 10)
            };
        })())
    """)
    
    logger.info(f"Knowledge files search result: {json.dumps(knowledge_files, indent=2)}")
    
    # Approach 2: Look for specific file indicators
    file_info = client.evaluate_expression("""
        JSON.stringify((() => {
            const results = [];
            
            // Find all elements containing "lines" which might indicate file info
            const elements = Array.from(document.querySelectorAll('*')).filter(el => {
                const text = el.textContent || '';
                return text.includes('lines') && text.split(' ').length < 10;
            });
            
            elements.forEach(el => {
                const text = el.textContent.trim();
                // Look for parent or sibling that might have filename
                let filename = null;
                
                // Check previous sibling
                if (el.previousElementSibling) {
                    filename = el.previousElementSibling.textContent.trim();
                }
                // Check parent's previous sibling
                else if (el.parentElement && el.parentElement.previousElementSibling) {
                    filename = el.parentElement.previousElementSibling.textContent.trim();
                }
                
                if (filename && filename.length < 50) {
                    results.push({
                        filename: filename,
                        info: text
                    });
                }
            });
            
            return results.slice(0, 10);
        })())
    """)
    
    logger.info(f"File info found: {json.dumps(file_info, indent=2)}")
    
    # Approach 3: Try to click on knowledge files and extract content
    # Based on the patterns we found, try to click and extract
    if knowledge_files.get('filePatterns'):
        logger.info("\nAttempting to extract file contents...")
        
        for pattern in knowledge_files['filePatterns'][:2]:  # Try first 2 files
            logger.info(f"\nProcessing: {pattern}")
            
            # Try to click on the file
            click_result = client.evaluate_expression(f"""
                (() => {{
                    // Find element containing this text
                    const elements = Array.from(document.querySelectorAll('*')).filter(el => 
                        el.textContent && el.textContent.trim() === '{pattern}'
                    );
                    
                    if (elements.length > 0) {{
                        // Try to find clickable parent
                        let clickable = elements[0];
                        let current = elements[0];
                        
                        while (current && current.parentElement) {{
                            if (current.getAttribute('role') === 'button' || 
                                current.tagName === 'BUTTON' ||
                                current.getAttribute('tabindex') === '0') {{
                                clickable = current;
                                break;
                            }}
                            current = current.parentElement;
                        }}
                        
                        clickable.click();
                        return 'clicked';
                    }}
                    return 'not found';
                }})()
            """)
            
            logger.info(f"Click result: {click_result}")
            
            if click_result == 'clicked':
                time.sleep(1)  # Wait for content to load
                
                # Try to extract file content
                content = client.evaluate_expression("""
                    JSON.stringify((() => {
                        // Look for code blocks or content areas
                        const codeBlocks = document.querySelectorAll('pre, code, [class*="code"], [class*="content"]');
                        const contents = [];
                        
                        codeBlocks.forEach(block => {
                            const text = block.textContent || '';
                            if (text.length > 50) {  // Substantial content
                                contents.push(text);
                            }
                        });
                        
                        // Also check for modal or overlay content
                        const modals = document.querySelectorAll('[role="dialog"], [class*="modal"], [class*="overlay"]');
                        modals.forEach(modal => {
                            const text = modal.textContent || '';
                            if (text.length > 50) {
                                contents.push(text);
                            }
                        });
                        
                        return contents;
                    })())
                """)
                
                if content and len(content) > 0:
                    logger.info(f"\nFound content ({len(content)} blocks)")
                    for i, block in enumerate(content[:1]):  # Show first block
                        lines = block.split('\n')[:5]
                        logger.info(f"\nFirst 5 lines of content block {i+1}:")
                        for j, line in enumerate(lines, 1):
                            logger.info(f"  {j}: {line}")
                else:
                    logger.info("No content found after clicking")


def main():
    """Main function."""
    logger.info("DLPoS Project Knowledge Extraction Test")
    logger.info("=" * 60)
    
    with RobustChromeClient() as client:
        # Connect to Claude
        pages = client.get_pages()
        claude_page = None
        for page in pages:
            if 'claude.ai' in page.get('url', ''):
                claude_page = page
                break
        
        if not claude_page:
            logger.error("No Claude.ai page found. Please open Claude.ai in Chrome")
            return
        
        logger.info("Connecting to Claude...")
        client.connect_to_page(claude_page)
        
        try:
            extract_dlpos_knowledge(client)
        except Exception as e:
            logger.error(f"Error during extraction: {e}", exc_info=True)


if __name__ == "__main__":
    main()