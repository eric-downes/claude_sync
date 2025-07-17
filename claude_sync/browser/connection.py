"""Type-safe Chrome connection wrapper."""
import logging
from pathlib import Path
from typing import List, Optional
from contextlib import asynccontextmanager

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
        
        # Check for and handle GDPR/cookie notices
        await self._handle_cookie_notices()
    
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
        try:
            async with self.open_file_modal(file_name) as page:
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
                    return all_text
                
                # If still no content, log what we see for debugging
                logger.warning(f"Could not find content for {file_name} after clicking")
                return None
                
        except Exception as e:
            logger.error(f"Failed to download file '{file_name}': {e}")
            # Context manager ensures modal is closed even on error
            
            # If we're getting repeated failures, try aggressive cleanup
            if "not found on page" not in str(e):
                logger.warning("Attempting aggressive modal cleanup after download failure")
                await self.force_close_all_modals()
            
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
    
    async def force_close_all_modals(self) -> None:
        """Aggressively close all modals, dialogs, and popups to return to clean state."""
        page = await self.get_or_create_page()
        logger.info("Force closing all modals and popups")
        
        try:
            # Strategy 1: Use JavaScript to find and close all dialogs/modals
            await page.evaluate('''
                () => {
                    // First, close any open editable fields (like project description)
                    const activeElement = document.activeElement;
                    if (activeElement && (activeElement.tagName === 'TEXTAREA' || 
                        activeElement.tagName === 'INPUT' || 
                        activeElement.contentEditable === 'true')) {
                        activeElement.blur();
                        // Click outside the element to ensure it closes
                        document.body.click();
                    }
                    
                    // Find all elements with role="dialog"
                    const dialogs = document.querySelectorAll('[role="dialog"], [aria-modal="true"]');
                    dialogs.forEach(dialog => {
                        // Try to find close button within dialog using valid CSS selectors
                        const closeSelectors = [
                            'button[aria-label*="close" i]',
                            'button[aria-label*="Close" i]',
                            '[class*="close-button"]',
                            '[class*="close-btn"]',
                            '[class*="modal-close"]',
                            'button[title*="close" i]',
                            'button[title*="Close" i]'
                        ];
                        
                        let closeBtn = null;
                        for (const selector of closeSelectors) {
                            closeBtn = dialog.querySelector(selector);
                            if (closeBtn) break;
                        }
                        
                        // Also look for buttons with close text
                        if (!closeBtn) {
                            const buttons = dialog.querySelectorAll('button');
                            for (const btn of buttons) {
                                const text = btn.textContent || btn.innerText || '';
                                if (text.match(/^(×|X|Close|Cancel)$/i)) {
                                    closeBtn = btn;
                                    break;
                                }
                            }
                        }
                        
                        if (closeBtn) {
                            closeBtn.click();
                        } else {
                            // If no close button, try to remove the dialog
                            dialog.style.display = 'none';
                            // Also try to remove parent overlay if exists
                            const parent = dialog.parentElement;
                            if (parent && (parent.className.includes('overlay') || 
                                         parent.className.includes('modal') ||
                                         parent.className.includes('backdrop'))) {
                                parent.style.display = 'none';
                            }
                        }
                    });
                    
                    // Find and hide any overlay/backdrop elements
                    const overlays = document.querySelectorAll(
                        '[class*="overlay"], [class*="backdrop"], [class*="modal-backdrop"], ' +
                        '[class*="modal-overlay"], [class*="dialog-overlay"]'
                    );
                    overlays.forEach(overlay => {
                        overlay.style.display = 'none';
                    });
                    
                    // Remove any body classes that might indicate modal state
                    document.body.classList.remove('modal-open', 'has-modal', 'overflow-hidden');
                    document.body.style.overflow = '';
                    document.documentElement.style.overflow = '';
                }
            ''')
            
            # Strategy 2: Press Escape multiple times
            for _ in range(3):
                await page.keyboard.press('Escape')
                await page.wait_for_timeout(100)
            
            # Strategy 3: Try to click on body/main content to dismiss any click-away modals
            await page.evaluate('''
                () => {
                    // Click on body
                    document.body.click();
                    
                    // Try to find main content area and click it
                    const main = document.querySelector('main, [role="main"], #main, .main-content');
                    if (main) {
                        main.click();
                    }
                }
            ''')
            
            # Strategy 4: Try common keyboard shortcuts
            await page.keyboard.press('Escape')
            await page.wait_for_timeout(100)
            
            # Strategy 5: Force close any specific Claude.ai modals
            await page.evaluate('''
                () => {
                    // Look for Claude-specific modal patterns
                    const modals = document.querySelectorAll(
                        'div[data-radix-portal], ' +  // Radix UI portals
                        'div[data-reach-dialog-overlay], ' +  // Reach UI dialogs
                        'div[class*="DialogOverlay"], ' +
                        'div[class*="Modal"], ' +
                        'div[class*="Popup"]'
                    );
                    modals.forEach(modal => {
                        modal.remove();
                    });
                }
            ''')
            
            # Wait a bit for any animations to complete
            await page.wait_for_timeout(500)
            
            logger.info("Completed force close of all modals")
            
        except Exception as e:
            logger.error(f"Error during force close modals: {e}")
            # Even if there's an error, try one last escape
            try:
                await page.keyboard.press('Escape')
            except:
                pass
    
    async def _handle_cookie_notices(self) -> None:
        """Detect and handle GDPR/cookie consent notices."""
        page = await self.get_or_create_page()
        
        try:
            # Common cookie consent button selectors
            cookie_selectors = [
                # Generic accept buttons
                'button:has-text("Accept all")',
                'button:has-text("Accept All")',
                'button:has-text("Accept")',
                'button:has-text("I agree")',
                'button:has-text("I Agree")',
                'button:has-text("Agree")',
                'button:has-text("OK")',
                'button:has-text("Got it")',
                'button:has-text("Continue")',
                # Cookie-specific
                'button[id*="cookie-accept"]',
                'button[class*="cookie-accept"]',
                'button[id*="accept-cookies"]',
                'button[class*="accept-cookies"]',
                # GDPR-specific
                'button[id*="gdpr-accept"]',
                'button[class*="gdpr-accept"]',
                # OneTrust common IDs
                '#onetrust-accept-btn-handler',
                'button#onetrust-accept-btn-handler',
                # Other common frameworks
                '.cookie-consent-accept',
                '.gdpr-accept',
                '[data-testid*="cookie-accept"]',
                '[data-testid*="accept-cookies"]',
            ]
            
            # Wait a short time for any cookie notice to appear
            await page.wait_for_timeout(1000)
            
            # Try each selector
            for selector in cookie_selectors:
                try:
                    button = await page.query_selector(selector)
                    if button and await button.is_visible():
                        logger.info(f"Found cookie consent button with selector: {selector}")
                        await button.click()
                        await page.wait_for_timeout(500)
                        return
                except Exception:
                    continue
            
            # Check for cookie banner by common class/id patterns
            banner_selectors = [
                '[class*="cookie-banner"]',
                '[class*="cookie-consent"]',
                '[class*="gdpr"]',
                '[id*="cookie-banner"]',
                '[id*="cookie-consent"]',
                '[role="dialog"][aria-label*="cookie" i]',
                '[role="dialog"][aria-label*="consent" i]',
            ]
            
            for selector in banner_selectors:
                try:
                    banner = await page.query_selector(selector)
                    if banner and await banner.is_visible():
                        logger.info(f"Cookie banner detected with selector: {selector}")
                        # Banner exists but we couldn't find accept button
                        logger.warning("Cookie banner found but no accept button located")
                        break
                except Exception:
                    continue
                    
        except Exception as e:
            logger.debug(f"Error handling cookie notices: {e}")
    
    @asynccontextmanager
    async def open_file_modal(self, file_name: str):
        """Context manager for opening a file modal with automatic cleanup.
        
        Args:
            file_name: Name of file to open
            
        Yields:
            Page object with modal open
            
        Example:
            async with connection.open_file_modal("myfile.txt") as page:
                content = await extract_content(page)
        """
        page = await self.get_or_create_page()
        modal_opened = False
        
        # Ensure clean state before opening new modal
        await self.ensure_clean_state()
        
        try:
            # Find and click the file thumbnail
            thumbnails = await page.query_selector_all('div[data-testid="file-thumbnail"]')
            
            for thumb in thumbnails:
                h3 = await thumb.query_selector('h3')
                if h3:
                    name = await h3.text_content()
                    if name and name.strip() == file_name:
                        button = await thumb.query_selector('button')
                        if button:
                            logger.info(f"Opening modal for file: {file_name}")
                            await button.click()
                            modal_opened = True
                            
                            # Wait for modal to appear
                            await page.wait_for_timeout(1500)
                            
                            # Yield control to caller
                            yield page
                            break
            else:
                raise Exception(f"File '{file_name}' not found on page")
                
        finally:
            # Always try to close modal on exit
            if modal_opened:
                logger.debug(f"Closing modal for file: {file_name}")
                await self._close_modal(page)
                # Extra wait to ensure modal is fully closed
                await page.wait_for_timeout(500)
                
                # Double-check modal is closed by looking for dialog elements
                dialog_count = await page.locator('[role="dialog"], [aria-modal="true"]').count()
                if dialog_count > 0:
                    logger.warning(f"Modal still open after close attempt, using force close")
                    await self.force_close_all_modals()
    
    async def is_modal_open(self) -> bool:
        """Check if any modal/dialog is currently open."""
        page = await self.get_or_create_page()
        try:
            dialog_count = await page.locator('[role="dialog"], [aria-modal="true"]').count()
            return dialog_count > 0
        except:
            return False
    
    async def ensure_clean_state(self) -> None:
        """Ensure we're in a clean state with no modals open."""
        if await self.is_modal_open():
            logger.info("Modal detected, cleaning up state")
            await self.force_close_all_modals()
    
    async def close(self) -> None:
        """Close current page."""
        if self._current_page and not self._current_page.is_closed():
            await self._current_page.close()
            self._current_page = None