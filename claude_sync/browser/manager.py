"""Chrome browser process management."""
import asyncio
import logging
from typing import Optional

import psutil
from playwright.async_api import Browser, BrowserContext, async_playwright, Playwright

from .config import BrowserConfig

logger = logging.getLogger(__name__)


class ChromeManager:
    """Manages Chrome browser lifecycle and connections."""
    
    def __init__(self, config: BrowserConfig) -> None:
        """Initialize Chrome manager.
        
        Args:
            config: Browser configuration
        """
        self.config = config
        self._browser: Optional[BrowserContext] = None
        self._playwright: Optional[Playwright] = None
    
    def is_chrome_running(self) -> bool:
        """Check if Chrome is running with remote debugging.
        
        Returns:
            True if Chrome is running with debugging port
        """
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if 'chrome' in proc.info['name'].lower():
                    cmdline = proc.info.get('cmdline', [])
                    if any(f'--remote-debugging-port={self.config.remote_debugging_port}' in arg 
                           for arg in cmdline):
                        return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False
    
    def get_chrome_pid(self) -> Optional[int]:
        """Get Chrome process ID if running.
        
        Returns:
            Process ID or None
        """
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if 'chrome' in proc.info['name'].lower():
                    cmdline = proc.info.get('cmdline', [])
                    if any(f'--remote-debugging-port={self.config.remote_debugging_port}' in arg 
                           for arg in cmdline):
                        return proc.info['pid']
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return None
    
    def get_memory_usage(self) -> float:
        """Get Chrome memory usage in MB.
        
        Returns:
            Memory usage in MB or 0.0 if not running
        """
        pid = self.get_chrome_pid()
        if not pid:
            return 0.0
        
        try:
            process = psutil.Process(pid)
            memory_info = process.memory_info()
            return memory_info.rss / (1024 * 1024)  # Convert to MB
        except psutil.NoSuchProcess:
            return 0.0
    
    async def launch_persistent(self) -> BrowserContext:
        """Launch persistent Chrome instance with user profile.
        
        Returns:
            Browser context
        """
        if not self._playwright:
            self._playwright = await async_playwright().start()
        
        logger.info(f"Launching Chrome with profile: {self.config.user_data_dir}")
        
        # Ensure user data directory exists
        self.config.user_data_dir.mkdir(parents=True, exist_ok=True)
        
        # Launch persistent context
        browser = await self._playwright.chromium.launch_persistent_context(
            str(self.config.user_data_dir),
            headless=self.config.headless,
            args=self.config.get_chrome_args(),
            viewport=self.config.get_viewport(),
            ignore_default_args=["--enable-automation"],
            channel="chrome",  # Use stable Chrome
        )
        
        self._browser = browser
        return browser
    
    async def connect_existing(self) -> Optional[BrowserContext]:
        """Connect to existing Chrome instance if available.
        
        Returns:
            Browser context or None if not running
        """
        if not self.is_chrome_running():
            logger.info("No existing Chrome instance found")
            return None
        
        try:
            if not self._playwright:
                self._playwright = await async_playwright().start()
            
            logger.info(f"Connecting to Chrome on port {self.config.remote_debugging_port}")
            
            # Connect over CDP
            browser = await self._playwright.chromium.connect_over_cdp(
                f"http://localhost:{self.config.remote_debugging_port}"
            )
            
            # Get the default context (persistent context)
            contexts = browser.contexts
            if contexts:
                self._browser = contexts[0]
                return contexts[0]
            
            # Create new context if none exists
            context = await browser.new_context(
                viewport=self.config.get_viewport(),
            )
            self._browser = context
            return context
            
        except Exception as e:
            logger.error(f"Failed to connect to Chrome: {e}")
            return None
    
    async def get_or_create_browser(self) -> BrowserContext:
        """Get existing browser or create new one.
        
        Returns:
            Browser context
        """
        # Try to connect to existing instance first
        browser = await self.connect_existing()
        if browser:
            return browser
        
        # Launch new instance
        return await self.launch_persistent()
    
    async def close(self) -> None:
        """Close browser and cleanup resources."""
        if self._browser:
            try:
                await self._browser.close()
            except Exception as e:
                logger.error(f"Error closing browser: {e}")
            self._browser = None
        
        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception as e:
                logger.error(f"Error stopping playwright: {e}")
            self._playwright = None
    
    def kill_chrome(self) -> None:
        """Force kill Chrome process if running."""
        pid = self.get_chrome_pid()
        if not pid:
            return
        
        try:
            process = psutil.Process(pid)
            process.terminate()
            try:
                process.wait(timeout=5)
            except psutil.TimeoutExpired:
                logger.warning("Chrome didn't terminate gracefully, force killing")
                process.kill()
        except psutil.NoSuchProcess:
            pass