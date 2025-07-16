"""Tests for browser management."""
import asyncio
import sys
from pathlib import Path
from typing import AsyncGenerator, Generator
from unittest.mock import Mock, patch, AsyncMock, MagicMock

import pytest
import psutil
from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from claude_sync.browser import ChromeManager, ChromeConnection, BrowserConfig


class TestChromeManager:
    """Test ChromeManager class."""
    
    @pytest.fixture
    def config(self) -> BrowserConfig:
        """Create test browser config."""
        return BrowserConfig(
            headless=True,
            user_data_dir=Path("/tmp/test-chrome-profile"),
            memory_limit_mb=100,
            remote_debugging_port=9222,
        )
    
    @pytest.fixture
    def manager(self, config: BrowserConfig) -> ChromeManager:
        """Create ChromeManager instance."""
        return ChromeManager(config)
    
    def test_init(self, config: BrowserConfig):
        """Test ChromeManager initialization."""
        manager = ChromeManager(config)
        assert manager.config == config
        assert manager._browser is None
        assert manager._playwright is None
    
    @patch("psutil.Process")
    def test_is_chrome_running(self, mock_process, manager: ChromeManager):
        """Test checking if Chrome is running."""
        # Test when Chrome is running
        mock_proc = Mock()
        mock_proc.name.return_value = "chrome"
        mock_proc.cmdline.return_value = ["chrome", "--remote-debugging-port=9222"]
        
        # Mock process_iter to return proper dict structure
        mock_proc.info = {'pid': 123, 'name': 'chrome', 'cmdline': ["chrome", "--remote-debugging-port=9222"]}
        mock_proc.pid = 123
        
        with patch("psutil.process_iter", return_value=[mock_proc]):
            assert manager.is_chrome_running() is True
            assert manager.get_chrome_pid() == 123
        
        # Test when Chrome is not running
        mock_proc.info = {'pid': 456, 'name': 'firefox', 'cmdline': ["firefox"]}
        with patch("psutil.process_iter", return_value=[mock_proc]):
            assert manager.is_chrome_running() is False
            assert manager.get_chrome_pid() is None
    
    @patch("psutil.Process")
    def test_get_memory_usage(self, mock_process_class, manager: ChromeManager):
        """Test getting Chrome memory usage."""
        # Test when Chrome is running
        mock_proc = Mock()
        mock_proc.memory_info.return_value = Mock(rss=100 * 1024 * 1024)  # 100MB
        mock_process_class.return_value = mock_proc
        
        with patch.object(manager, "get_chrome_pid", return_value=123):
            assert manager.get_memory_usage() == 100.0
        
        # Test when Chrome is not running
        with patch.object(manager, "get_chrome_pid", return_value=None):
            assert manager.get_memory_usage() == 0.0
        
        # Test when process doesn't exist
        mock_process_class.side_effect = psutil.NoSuchProcess(123)
        with patch.object(manager, "get_chrome_pid", return_value=123):
            assert manager.get_memory_usage() == 0.0
    
    @pytest.mark.asyncio
    async def test_launch_persistent(self, manager: ChromeManager):
        """Test launching persistent Chrome instance."""
        # Mock playwright
        mock_pw = AsyncMock()
        mock_browser = AsyncMock()
        mock_pw.chromium.launch_persistent_context.return_value = mock_browser
        mock_pw.start.return_value = mock_pw
        
        # Create a mock that behaves like async_playwright()
        mock_async_pw = MagicMock()
        mock_async_pw.start = AsyncMock(return_value=mock_pw)
        
        with patch("claude_sync.browser.manager.async_playwright", return_value=mock_async_pw):
            
            # Launch browser
            browser = await manager.launch_persistent()
            
            # Verify correct launch parameters
            mock_pw.chromium.launch_persistent_context.assert_called_once()
            call_args = mock_pw.chromium.launch_persistent_context.call_args
            
            assert call_args[0][0] == str(manager.config.user_data_dir)
            assert call_args[1]["headless"] == manager.config.headless
            assert "--remote-debugging-port=9222" in call_args[1]["args"]
            assert browser == mock_browser
    
    @pytest.mark.asyncio
    async def test_connect_existing(self, manager: ChromeManager):
        """Test connecting to existing Chrome instance."""
        # Mock playwright
        mock_pw = AsyncMock()
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_browser.contexts = [mock_context]
        mock_pw.chromium.connect_over_cdp.return_value = mock_browser
        mock_pw.start.return_value = mock_pw
        
        # Create a mock that behaves like async_playwright()
        mock_async_pw = MagicMock()
        mock_async_pw.start = AsyncMock(return_value=mock_pw)
        
        with patch("claude_sync.browser.manager.async_playwright", return_value=mock_async_pw):
            # Mock Chrome running
            with patch.object(manager, "is_chrome_running", return_value=True):
                browser = await manager.connect_existing()
                
                mock_pw.chromium.connect_over_cdp.assert_called_once_with(
                    f"http://localhost:{manager.config.remote_debugging_port}"
                )
                assert browser == mock_context
            
            # Test when Chrome is not running
            with patch.object(manager, "is_chrome_running", return_value=False):
                browser = await manager.connect_existing()
                assert browser is None
    
    @pytest.mark.asyncio
    async def test_get_or_create_browser(self, manager: ChromeManager):
        """Test get_or_create_browser logic."""
        mock_browser = AsyncMock()
        
        # Test when can connect to existing
        with patch.object(manager, "connect_existing", return_value=mock_browser):
            browser = await manager.get_or_create_browser()
            assert browser == mock_browser
        
        # Test when need to launch new
        with patch.object(manager, "connect_existing", return_value=None):
            with patch.object(manager, "launch_persistent", return_value=mock_browser):
                browser = await manager.get_or_create_browser()
                assert browser == mock_browser
    
    @pytest.mark.asyncio
    async def test_close(self, manager: ChromeManager):
        """Test closing browser and playwright."""
        mock_browser = AsyncMock()
        mock_playwright = AsyncMock()
        
        manager._browser = mock_browser
        manager._playwright = mock_playwright
        
        await manager.close()
        
        mock_browser.close.assert_called_once()
        mock_playwright.stop.assert_called_once()
        assert manager._browser is None
        assert manager._playwright is None
    
    def test_kill_chrome(self, manager: ChromeManager):
        """Test killing Chrome process."""
        mock_proc = Mock()
        
        with patch("claude_sync.browser.manager.psutil.Process", return_value=mock_proc) as mock_process_class:
            with patch.object(manager, "get_chrome_pid", return_value=123):
                manager.kill_chrome()
                
                mock_process_class.assert_called_once_with(123)
                mock_proc.terminate.assert_called_once()
                mock_proc.wait.assert_called_once_with(timeout=5)
        
        # Test force kill on timeout
        mock_proc.reset_mock()
        mock_proc.wait.side_effect = psutil.TimeoutExpired(5, 123)
        with patch("claude_sync.browser.manager.psutil.Process", return_value=mock_proc):
            with patch.object(manager, "get_chrome_pid", return_value=123):
                manager.kill_chrome()
                mock_proc.kill.assert_called_once()


class TestChromeConnection:
    """Test ChromeConnection wrapper class."""
    
    @pytest.fixture
    async def mock_page(self) -> AsyncMock:
        """Create mock page."""
        page = AsyncMock(spec=Page)
        page.url = "https://claude.ai"
        page.is_closed.return_value = False
        page.goto = AsyncMock()
        page.content = AsyncMock(return_value="<html>Test</html>")
        page.wait_for_selector = AsyncMock()
        page.wait_for_timeout = AsyncMock()
        page.locator = MagicMock()
        return page
    
    @pytest.fixture
    async def mock_context(self, mock_page: AsyncMock) -> AsyncMock:
        """Create mock browser context."""
        context = AsyncMock(spec=BrowserContext)
        context.pages = [mock_page]
        context.new_page.return_value = mock_page
        return context
    
    @pytest.fixture
    async def connection(self, mock_context: AsyncMock) -> ChromeConnection:
        """Create ChromeConnection instance."""
        return ChromeConnection(mock_context)
    
    @pytest.mark.asyncio
    async def test_init(self, mock_context: AsyncMock):
        """Test ChromeConnection initialization."""
        conn = ChromeConnection(mock_context)
        assert conn.context == mock_context
        assert conn._current_page is None
    
    @pytest.mark.asyncio
    async def test_get_or_create_page(self, connection: ChromeConnection, mock_page: AsyncMock):
        """Test getting or creating a page."""
        # Test when no current page (uses existing page from context.pages)
        page = await connection.get_or_create_page()
        assert page == mock_page
        assert connection._current_page == mock_page
        
        # Test when current page exists and not closed
        page2 = await connection.get_or_create_page()
        assert page2 == mock_page
        
        # Test when current page is closed
        mock_page.is_closed.return_value = True
        connection.context.pages = []  # No existing pages
        new_page = AsyncMock()
        connection.context.new_page.return_value = new_page
        
        page3 = await connection.get_or_create_page()
        assert page3 == new_page
        connection.context.new_page.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_navigate(self, connection: ChromeConnection, mock_page: AsyncMock):
        """Test navigating to URL."""
        mock_page.is_closed.return_value = False
        
        url = "https://claude.ai/projects"
        await connection.navigate(url)
        
        mock_page.goto.assert_called_once_with(url, wait_until="networkidle")
        assert connection._current_page == mock_page
    
    @pytest.mark.asyncio
    async def test_get_page_content(self, connection: ChromeConnection, mock_page: AsyncMock):
        """Test getting page content."""
        mock_page.is_closed.return_value = False
        mock_page.content.return_value = "<html>Test</html>"
        
        content = await connection.get_page_content()
        assert content == "<html>Test</html>"
        mock_page.content.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_wait_for_selector(self, connection: ChromeConnection, mock_page: AsyncMock):
        """Test waiting for selector."""
        mock_page.is_closed.return_value = False
        
        selector = "div.project-card"
        mock_element = AsyncMock()
        mock_page.wait_for_selector.return_value = mock_element
        
        element = await connection.wait_for_selector(selector, timeout=5000)
        
        assert element == mock_element
        mock_page.wait_for_selector.assert_called_once_with(
            selector, timeout=5000
        )
    
    @pytest.mark.asyncio
    async def test_is_logged_in(self, connection: ChromeConnection, mock_page: AsyncMock):
        """Test checking login status."""
        # Add required methods
        mock_page.is_closed.return_value = False
        mock_page.wait_for_timeout = AsyncMock()
        
        # Test when logged in (on projects page)
        mock_page.url = "https://claude.ai/projects"
        mock_locator = AsyncMock()
        mock_locator.count.return_value = 0  # No login button
        mock_page.locator.return_value = mock_locator
        
        assert await connection.is_logged_in() is True
        
        # Test when not logged in (has login button)
        mock_page.url = "https://claude.ai/login"
        mock_locator.count.return_value = 1  # Has login button
        
        assert await connection.is_logged_in() is False
    
    @pytest.mark.asyncio
    async def test_extract_projects(self, connection: ChromeConnection, mock_page: AsyncMock):
        """Test extracting projects from current page."""
        from tests.fixtures.html_samples import PROJECTS_PAGE_HTML
        
        mock_page.is_closed.return_value = False
        mock_page.content.return_value = PROJECTS_PAGE_HTML
        
        projects = await connection.extract_projects()
        
        assert len(projects) == 4
        assert projects[0].name == "DNI"
        assert projects[0].description == "EU-only MLETR"
    
    @pytest.mark.asyncio
    async def test_extract_knowledge_files(self, connection: ChromeConnection, mock_page: AsyncMock):
        """Test extracting knowledge files from current page."""
        from tests.fixtures.html_samples import DNI_PROJECT_PAGE_HTML
        
        mock_page.is_closed.return_value = False
        mock_page.content.return_value = DNI_PROJECT_PAGE_HTML
        
        files = await connection.extract_knowledge_files()
        
        assert len(files) == 7
        assert files[0].name == "Invoice valuation"
        assert files[0].lines == 489
    
    @pytest.mark.asyncio
    async def test_download_file_content(self, connection: ChromeConnection, mock_page: AsyncMock):
        """Test downloading file content."""
        # Add required methods
        mock_page.is_closed.return_value = False
        
        # Mock file download
        mock_download = AsyncMock()
        mock_download.path.return_value = "/tmp/downloaded.txt"
        
        # Mock locator
        mock_locator = MagicMock()
        mock_locator.count = AsyncMock(return_value=1)
        mock_locator.click = AsyncMock()
        mock_page.locator.return_value = mock_locator
        
        # Mock expect_download properly
        class DownloadContext:
            async def __aenter__(self):
                return self
            async def __aexit__(self, *args):
                return None
            @property
            def value(self):
                return Promise(mock_download)
                
        class Promise:
            def __init__(self, val):
                self._val = val
            def __await__(self):
                async def _return_val():
                    return self._val
                return _return_val().__await__()
        
        mock_page.expect_download = MagicMock(return_value=DownloadContext())
        
        with patch("aiofiles.open", create=True) as mock_open:
            mock_file = AsyncMock()
            mock_file.read.return_value = "File content"
            mock_open.return_value.__aenter__.return_value = mock_file
            
            with patch("pathlib.Path.unlink"):
                content = await connection.download_file_content("test.txt")
            
            assert content == "File content"
    
    @pytest.mark.asyncio
    async def test_close(self, connection: ChromeConnection, mock_page: AsyncMock):
        """Test closing connection."""
        mock_page.is_closed.return_value = False
        connection._current_page = mock_page
        
        await connection.close()
        
        mock_page.close.assert_called_once()
        assert connection._current_page is None


class TestBrowserConfig:
    """Test BrowserConfig model."""
    
    def test_default_config(self):
        """Test default browser configuration."""
        config = BrowserConfig()
        
        assert config.headless is True
        assert config.user_data_dir == Path.home() / ".claude-sync" / "chrome-profile"
        assert config.memory_limit_mb == 100
        assert config.remote_debugging_port == 9222
        assert config.viewport_width == 1280
        assert config.viewport_height == 720
    
    def test_custom_config(self):
        """Test custom browser configuration."""
        config = BrowserConfig(
            headless=False,
            user_data_dir=Path("/custom/path"),
            memory_limit_mb=200,
            remote_debugging_port=9333,
        )
        
        assert config.headless is False
        assert config.user_data_dir == Path("/custom/path")
        assert config.memory_limit_mb == 200
        assert config.remote_debugging_port == 9333
    
    def test_chrome_args(self):
        """Test Chrome launch arguments."""
        config = BrowserConfig()
        args = config.get_chrome_args()
        
        assert "--no-sandbox" in args
        assert "--disable-setuid-sandbox" in args
        assert f"--remote-debugging-port={config.remote_debugging_port}" in args
        assert "--disable-blink-features=AutomationControlled" in args
        
        # Memory optimization flags
        assert "--memory-pressure-off" in args
        assert "--max_old_space_size=96" in args
    
    def test_viewport_settings(self):
        """Test viewport configuration."""
        config = BrowserConfig(viewport_width=1920, viewport_height=1080)
        
        viewport = config.get_viewport()
        assert viewport["width"] == 1920
        assert viewport["height"] == 1080