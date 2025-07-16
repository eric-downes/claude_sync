#!/usr/bin/env python3
"""
Extract and display knowledge files from DLPoS project.
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


def click_knowledge_file(client, filename):
    """Click on a specific knowledge file."""
    logger.info(f"Attempting to click on: {filename}")
    
    # Try to click on the file
    click_result = client.evaluate_expression(f"""
        (() => {{
            // Find the file by name
            const elements = Array.from(document.querySelectorAll('*')).filter(el => {{
                const text = el.textContent || '';
                return text.includes('{filename}') && text.includes('lines');
            }});
            
            console.log('Found elements:', elements.length);
            
            for (let el of elements) {{
                // Look for clickable ancestor
                let current = el;
                while (current) {{
                    // Check if this element or its children contain just the filename
                    const hasFilename = Array.from(current.querySelectorAll('*')).some(child => 
                        child.textContent.trim() === '{filename}'
                    ) || current.textContent.trim() === '{filename}';
                    
                    if (hasFilename && (
                        current.getAttribute('role') === 'button' || 
                        current.tagName === 'BUTTON' ||
                        current.hasAttribute('tabindex') ||
                        current.style.cursor === 'pointer'
                    )) {{
                        console.log('Clicking on:', current);
                        current.click();
                        return 'clicked';
                    }}
                    current = current.parentElement;
                }}
            }}
            
            // Fallback: try to find and click the filename text directly
            const fileElements = Array.from(document.querySelectorAll('*')).filter(el => 
                el.textContent.trim() === '{filename}'
            );
            
            for (let el of fileElements) {{
                // Try clicking the element itself
                el.click();
                
                // Also try clicking its parent
                if (el.parentElement) {{
                    el.parentElement.click();
                }}
                
                return 'clicked-fallback';
            }}
            
            return 'not-found';
        }})()
    """)
    
    logger.info(f"Click result: {click_result}")
    return click_result


def extract_file_content(client):
    """Extract content after clicking on a file."""
    # Wait for content to potentially load
    time.sleep(2)
    
    # Try multiple strategies to find content
    content_data = client.evaluate_expression("""
        JSON.stringify((() => {
            const results = {
                found: false,
                content: null,
                method: null
            };
            
            // Strategy 1: Look for modal/dialog content
            const modals = document.querySelectorAll('[role="dialog"], [class*="modal"], [class*="overlay"], [class*="sheet"]');
            for (let modal of modals) {
                const codeBlocks = modal.querySelectorAll('pre, code, [class*="code"]');
                if (codeBlocks.length > 0) {
                    results.found = true;
                    results.content = codeBlocks[0].textContent;
                    results.method = 'modal-code';
                    return results;
                }
                
                // Check if modal has substantial text
                const text = modal.textContent || '';
                if (text.length > 100 && !text.includes('Project knowledge')) {
                    results.found = true;
                    results.content = text;
                    results.method = 'modal-text';
                    return results;
                }
            }
            
            // Strategy 2: Look for newly visible content areas
            const contentAreas = document.querySelectorAll('[class*="content"], [class*="viewer"], [class*="preview"]');
            for (let area of contentAreas) {
                // Check if it's visible and has content
                const rect = area.getBoundingClientRect();
                if (rect.width > 0 && rect.height > 0) {
                    const text = area.textContent || '';
                    if (text.length > 100) {
                        results.found = true;
                        results.content = text;
                        results.method = 'content-area';
                        return results;
                    }
                }
            }
            
            // Strategy 3: Look for any pre or code blocks on the page
            const allCode = document.querySelectorAll('pre, code');
            for (let code of allCode) {
                const text = code.textContent || '';
                if (text.length > 50) {
                    results.found = true;
                    results.content = text;
                    results.method = 'code-block';
                    return results;
                }
            }
            
            // Strategy 4: Check for significant text changes
            const bodyText = document.body.innerText;
            if (bodyText.includes('market plan') || bodyText.includes('research opinion')) {
                // Look for the content section
                const lines = bodyText.split('\\n');
                let inContent = false;
                let content = [];
                
                for (let line of lines) {
                    if (line.includes('2-sided market plan') || line.includes('ssv research opinion')) {
                        inContent = true;
                        continue;
                    }
                    if (inContent && line.trim()) {
                        content.push(line);
                        if (content.length >= 20) break;
                    }
                }
                
                if (content.length > 0) {
                    results.found = true;
                    results.content = content.join('\\n');
                    results.method = 'text-extraction';
                    return results;
                }
            }
            
            return results;
        })())
    """)
    
    return content_data


def close_modal(client):
    """Try to close any open modal."""
    client.evaluate_expression("""
        (() => {
            // Try to close modal by clicking outside
            const backdrop = document.querySelector('[class*="backdrop"], [class*="overlay"]');
            if (backdrop) backdrop.click();
            
            // Try escape key
            document.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape'}));
            
            // Try close button
            const closeButtons = document.querySelectorAll('[aria-label*="close" i], [aria-label*="dismiss" i], button[class*="close"]');
            closeButtons.forEach(btn => btn.click());
        })()
    """)
    time.sleep(1)


def main():
    """Main function."""
    logger.info("DLPoS Project Knowledge Files Extraction")
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
        
        # Navigate to DLPoS project
        logger.info("Navigating to DLPoS project...")
        client.navigate_and_wait("https://claude.ai/project/019800bd-979b-7116-864b-006d88133519")
        time.sleep(2)
        
        # Check current page
        page_info = client.get_page_content()
        logger.info(f"Current page: {page_info['url']}")
        
        # Process each file
        files = ["2-sided market plan", "ssv research opinion"]
        
        for filename in files:
            logger.info(f"\n{'='*60}")
            logger.info(f"Processing: {filename}")
            logger.info(f"{'='*60}")
            
            # Click on the file
            click_result = click_knowledge_file(client, filename)
            
            if 'clicked' in click_result:
                # Extract content
                content_data = extract_file_content(client)
                
                if content_data.get('found'):
                    logger.info(f"Content found using method: {content_data.get('method')}")
                    content = content_data.get('content', '')
                    
                    # Display first 5 lines
                    lines = content.split('\n')
                    logger.info(f"\nFirst 5 lines of '{filename}':")
                    for i, line in enumerate(lines[:5], 1):
                        logger.info(f"{i:3d}: {line}")
                    
                    if len(lines) > 5:
                        logger.info(f"     ... ({len(lines) - 5} more lines)")
                else:
                    logger.info("Could not extract content")
                
                # Close any modal
                close_modal(client)
            else:
                logger.info(f"Could not click on {filename}")


if __name__ == "__main__":
    main()