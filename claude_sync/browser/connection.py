"""Type-safe Chrome connection wrapper."""
import logging
from pathlib import Path
from typing import List, Optional

import aiofiles
from playwright.async_api import BrowserContext, Page, Download

from claude_sync.extractors import ProjectExtractor, KnowledgeExtractor
from claude_sync.models import Project, KnowledgeFile

logger = logging.getLogger(__name__)


class ChromeConnection:
    """Type-safe wrapper for Chrome browser operations."""
    
    def __init__(self, context: BrowserContext) -> None:
        """Initialize connection with browser context.
        
        Args:
            context: Playwright browser context
        """
        self.context = context
        self._current_page: Optional[Page] = None
    
    async def get_or_create_page(self) -> Page:
        """Get current page or create new one.
        
        Returns:
            Page instance
        """
        if self._current_page and not self._current_page.is_closed():
            return self._current_page
        
        # Try to use existing page
        pages = self.context.pages
        if pages:
            self._current_page = pages[0]
        else:
            self._current_page = await self.context.new_page()
        
        return self._current_page
    
    async def navigate(self, url: str, timeout: int = 60000) -> None:
        """Navigate to URL and wait for page to load.
        
        Args:
            url: URL to navigate to
            timeout: Navigation timeout in milliseconds (default: 60s)
        """
        page = await self.get_or_create_page()
        logger.info(f"Navigating to: {url}")
        await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
        self._current_page = page
    
    async def get_page_content(self) -> str:
        """Get current page HTML content.
        
        Returns:
            HTML content
        """
        page = await self.get_or_create_page()
        return await page.content()
    
    async def wait_for_selector(
        self, 
        selector: str, 
        timeout: int = 30000
    ) -> Optional[Page]:
        """Wait for selector to appear on page.
        
        Args:
            selector: CSS selector to wait for
            timeout: Timeout in milliseconds
            
        Returns:
            Page element or None if timeout
        """
        page = await self.get_or_create_page()
        try:
            element = await page.wait_for_selector(selector, timeout=timeout)
            return element
        except Exception as e:
            logger.warning(f"Selector '{selector}' not found: {e}")
            return None
    
    async def is_logged_in(self) -> bool:
        """Check if user is logged into Claude.
        
        Returns:
            True if logged in
        """
        page = await self.get_or_create_page()
        
        # Check if we're on a logged-in page
        if "/project" in page.url or "/chat" in page.url:
            return True
        
        # Navigate to Claude and check
        if page.url != "https://claude.ai":
            await self.navigate("https://claude.ai")
        
        # Wait a bit for redirect
        await page.wait_for_timeout(2000)
        
        # Check for login indicators
        if "login" in page.url:
            return False
        
        # Check for presence of login button
        login_button_count = await page.locator('button:has-text("Sign in"), button:has-text("Log in")').count()
        return login_button_count == 0
    
    async def extract_projects(self) -> List[Project]:
        """Extract projects from current page.
        
        Automatically clicks 'View All' if available to get all projects.
        
        Returns:
            List of projects
        """
        page = await self.get_or_create_page()
        
        # Check if we're on the projects page
        if "/projects" not in page.url:
            logger.warning(f"Not on projects page: {page.url}")
            html = await self.get_page_content()
            extractor = ProjectExtractor()
            return extractor.extract_from_html(html)
        
        # Look for "View All" button and click it if present
        try:
            view_all_button = await page.query_selector("button:has-text('View all')")
            if view_all_button and await view_all_button.is_visible():
                logger.info("Found 'View all' button, clicking to load all projects")
                await view_all_button.click()
                # Wait for projects to load
                await page.wait_for_timeout(2000)
        except Exception as e:
            logger.debug(f"No 'View all' button found or error clicking: {e}")
        
        # Extract projects
        html = await self.get_page_content()
        extractor = ProjectExtractor()
        return extractor.extract_from_html(html)
    
    async def extract_knowledge_files(self) -> List[KnowledgeFile]:
        """Extract knowledge files from current project page.
        
        Returns:
            List of knowledge files
        """
        html = await self.get_page_content()
        extractor = KnowledgeExtractor()
        return extractor.extract_from_html(html)
    
    async def download_file_content(self, file_name: str) -> Optional[str]:
        """Download content of a knowledge file by clicking and extracting from modal.
        
        Args:
            file_name: Name of file to download
            
        Returns:
            File content or None if failed
        """
        page = await self.get_or_create_page()
        
        try:
            # Find the file thumbnail by name
            thumbnails = await page.query_selector_all('div[data-testid="file-thumbnail"]')
            
            for thumb in thumbnails:
                # Check if this is our file
                h3 = await thumb.query_selector('h3')
                if h3:
                    name = await h3.text_content()
                    if name and name.strip() == file_name:
                        # Click the thumbnail to open the modal
                        button = await thumb.query_selector('button')
                        if button:
                            logger.info(f"Clicking on file: {file_name}")
                            await button.click()
                            
                            # Wait for modal to appear
                            await page.wait_for_timeout(1000)
                            
                            # Strategy 1: Look for modal/dialog content
                            # Wait a bit for modal to fully render
                            await page.wait_for_timeout(1500)
                            
                            # Use JavaScript to find the actual content more reliably
                            content_data = await page.evaluate('''
                                () => {
                                    // Find the modal
                                    const modal = document.querySelector('[role="dialog"]');
                                    if (!modal) return null;
                                    
                                    // Look for the main content div - it has specific styling
                                    // The actual content is usually in a monospace font div
                                    const contentSelectors = [
                                        'div[class*="font-mono"]',
                                        'div[class*="whitespace-pre-wrap"]',
                                        'pre',
                                        'code',
                                    ];
                                    
                                    for (const selector of contentSelectors) {
                                        const elements = modal.querySelectorAll(selector);
                                        for (const el of elements) {
                                            const text = el.textContent?.trim() || '';
                                            // Skip metadata lines
                                            if (text.includes('KB') && text.includes('lines') && text.length < 100) continue;
                                            if (text.includes('Formatting may be') && text.length < 100) continue;
                                            
                                            // If it's substantial content, return it
                                            if (text.length > 100) {
                                                return {
                                                    content: text,
                                                    selector: selector,
                                                    className: el.className
                                                };
                                            }
                                        }
                                    }
                                    
                                    // Fallback: get the longest text in the modal
                                    let longestText = '';
                                    const allElements = modal.querySelectorAll('*');
                                    for (const el of allElements) {
                                        const text = el.textContent?.trim() || '';
                                        if (text.length > longestText.length && 
                                            !text.includes('KB') && 
                                            !text.includes('Formatting may be')) {
                                            longestText = text;
                                        }
                                    }
                                    
                                    return longestText ? { content: longestText, selector: 'fallback' } : null;
                                }
                            ''')
                            
                            if content_data and content_data.get('content'):
                                logger.info(f"Found content via {content_data.get('selector', 'unknown')} ({len(content_data['content'])} chars)")
                                
                                # Close modal
                                await self._close_modal(page)
                                
                                return content_data['content'].strip()
                            
                            # Strategy 2: If no modal found, try getting all text from page
                            # Sometimes content appears in the main view
                            await page.wait_for_timeout(1000)
                            
                            # Get the full page text and look for file content
                            # This is less precise but can work as a fallback
                            all_text = await page.evaluate('''
                                () => {
                                    // Get all text content from the page
                                    const walker = document.createTreeWalker(
                                        document.body,
                                        NodeFilter.SHOW_TEXT,
                                        {
                                            acceptNode: function(node) {
                                                // Skip script and style tags
                                                const parent = node.parentElement;
                                                if (parent.tagName === 'SCRIPT' || parent.tagName === 'STYLE') {
                                                    return NodeFilter.FILTER_REJECT;
                                                }
                                                return NodeFilter.FILTER_ACCEPT;
                                            }
                                        },
                                        false
                                    );
                                    
                                    const texts = [];
                                    let node;
                                    while (node = walker.nextNode()) {
                                        const text = node.textContent.trim();
                                        if (text.length > 50) {  // Skip short texts
                                            texts.push(text);
                                        }
                                    }
                                    
                                    // Return the longest text block (likely the file content)
                                    return texts.sort((a, b) => b.length - a.length)[0] || '';
                                }
                            ''')
                            
                            if all_text and len(all_text) > 100:
                                logger.info(f"Found content via text extraction ({len(all_text)} chars)")
                                await self._close_modal(page)
                                return all_text
                            
                            # If still no content, log what we see for debugging
                            logger.warning(f"Could not find content for {file_name} after clicking")
                            
                            # Try to close any modal
                            await self._close_modal(page)
                            
                            return None
            
            logger.error(f"File '{file_name}' not found on page")
            return None
            
        except Exception as e:
            logger.error(f"Failed to download file '{file_name}': {e}")
            return None
    
    async def _close_modal(self, page: Page) -> None:
        """Try to close any open modal."""
        try:
            # Common close button selectors
            close_selectors = [
                'button[aria-label*="close" i]',
                'button[aria-label*="Close" i]',
                'button:has-text("Close")',
                'button:has-text("×")',
                'button:has-text("X")',
                '[class*="close"]',
            ]
            
            for selector in close_selectors:
                close_btn = await page.query_selector(selector)
                if close_btn and await close_btn.is_visible():
                    await close_btn.click()
                    await page.wait_for_timeout(500)
                    return
            
            # If no close button found, try pressing Escape
            await page.keyboard.press('Escape')
            
        except Exception as e:
            logger.debug(f"Error closing modal: {e}")
    
    async def close(self) -> None:
        """Close current page."""
        if self._current_page and not self._current_page.is_closed():
            await self._current_page.close()
            self._current_page = None