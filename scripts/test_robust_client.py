#!/usr/bin/env python3
"""
Test the robust Chrome client.
"""
import json
import logging

from src.chrome.robust_client import RobustChromeClient

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_robust_client():
    """Test the robust Chrome client."""
    with RobustChromeClient() as client:
        # Get pages
        pages = client.get_pages()
        logger.info(f"Found {len(pages)} pages:")
        for page in pages:
            logger.info(f"  - {page.get('title', 'Untitled')} ({page.get('url', '')[:50]}...)")
        
        # Find Claude page
        claude_page = None
        for page in pages:
            if 'claude.ai' in page.get('url', ''):
                claude_page = page
                break
        
        if claude_page:
            logger.info(f"\nConnecting to Claude page...")
            client.connect_to_page(claude_page)
            
            # Get current page content
            content = client.get_page_content()
            logger.info(f"\nClaude page content:")
            logger.info(f"  URL: {content['url']}")
            logger.info(f"  Title: {content['title']}")
            logger.info(f"  Ready state: {content['readyState']}")
            logger.info(f"  Has body: {content['hasBody']}")
            logger.info(f"  Body children: {content['bodyChildren']}")
            logger.info(f"  Forms: {content['forms']}")
            logger.info(f"  Inputs: {content['inputs']}")
            logger.info(f"  Buttons: {content['buttons']}")
            logger.info(f"  Links: {content['links']}")
            logger.info(f"  Body text preview: {content['bodyText'][:100]}...")
            
            # Test navigation to Google
            logger.info(f"\nNavigating to Google...")
            client.navigate_and_wait("https://www.google.com")
            
            # Get Google page content
            content = client.get_page_content()
            logger.info(f"\nGoogle page content:")
            logger.info(f"  URL: {content['url']}")
            logger.info(f"  Title: {content['title']}")
            logger.info(f"  Body children: {content['bodyChildren']}")
            logger.info(f"  Forms: {content['forms']}")
            logger.info(f"  Inputs: {content['inputs']}")
            
            # Navigate back to Claude
            logger.info(f"\nNavigating back to Claude projects...")
            client.navigate_and_wait("https://claude.ai/projects")
            
            # Get Claude projects content
            content = client.get_page_content()
            logger.info(f"\nClaude projects page content:")
            logger.info(f"  URL: {content['url']}")
            logger.info(f"  Body text preview: {content['bodyText'][:200]}...")
            
            # Try to find project links
            project_links = client.evaluate_expression("""
                Array.from(document.querySelectorAll('a[href*="/project/"]'))
                    .map(link => ({
                        text: link.innerText || link.textContent || '',
                        href: link.href
                    }))
                    .slice(0, 5)
            """)
            
            if project_links:
                logger.info(f"\nFound {len(project_links)} project links:")
                for link in project_links:
                    logger.info(f"  - {link['text'][:50]}...")
                
                # Navigate to first project
                first_project_url = project_links[0]['href']
                logger.info(f"\nNavigating to first project: {first_project_url}")
                client.navigate_and_wait(first_project_url)
                
                # Check project page
                content = client.get_page_content()
                logger.info(f"\nProject page content:")
                logger.info(f"  URL: {content['url']}")
                logger.info(f"  Body text preview: {content['bodyText'][:200]}...")
                
                # Look for knowledge section
                has_knowledge = client.evaluate_expression("""
                    (() => {
                        const pageText = document.body ? document.body.innerText.toLowerCase() : '';
                        return pageText.includes('knowledge') || 
                               pageText.includes('project files') ||
                               pageText.includes('add files');
                    })()
                """)
                logger.info(f"  Has knowledge section indicators: {has_knowledge}")


def main():
    """Main function."""
    logger.info("Testing Robust Chrome Client")
    logger.info("=" * 60)
    
    try:
        test_robust_client()
        logger.info("\n✓ Test completed successfully!")
    except Exception as e:
        logger.error(f"\n✗ Test failed: {e}", exc_info=True)


if __name__ == "__main__":
    main()