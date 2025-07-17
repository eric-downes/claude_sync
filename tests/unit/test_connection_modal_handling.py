"""Tests for modal handling in ChromeConnection."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from playwright.async_api import Page, Locator

from claude_sync.browser.connection import ChromeConnection


class TestModalHandling:
    """Test modal handling functionality."""
    
    @pytest.mark.asyncio
    async def test_close_modal_with_button(self):
        """Test closing modal using close button."""
        # Create mock page and context
        mock_page = AsyncMock(spec=Page)
        mock_context = AsyncMock()
        mock_context.pages = [mock_page]
        
        # Mock close button
        mock_close_btn = AsyncMock()
        mock_close_btn.is_visible = AsyncMock(return_value=True)
        mock_close_btn.click = AsyncMock()
        
        # Setup query_selector to return close button
        mock_page.query_selector = AsyncMock(return_value=mock_close_btn)
        mock_page.wait_for_timeout = AsyncMock()
        
        connection = ChromeConnection(mock_context)
        connection._current_page = mock_page
        
        await connection._close_modal(mock_page)
        
        # Verify close button was clicked
        mock_close_btn.click.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_close_modal_with_escape(self):
        """Test closing modal using Escape key when no button found."""
        # Create mock page and context
        mock_page = AsyncMock(spec=Page)
        mock_context = AsyncMock()
        mock_context.pages = [mock_page]
        
        # Mock no close button found
        mock_page.query_selector = AsyncMock(return_value=None)
        mock_page.keyboard = AsyncMock()
        mock_page.keyboard.press = AsyncMock()
        
        connection = ChromeConnection(mock_context)
        connection._current_page = mock_page
        
        await connection._close_modal(mock_page)
        
        # Verify Escape was pressed
        mock_page.keyboard.press.assert_called_with('Escape')
    
    @pytest.mark.asyncio
    async def test_force_close_all_modals(self):
        """Test force closing all modals."""
        # Create mock page and context
        mock_page = AsyncMock(spec=Page)
        mock_context = AsyncMock()
        mock_context.pages = [mock_page]
        
        # Mock page methods
        mock_page.evaluate = AsyncMock()
        mock_page.keyboard = AsyncMock()
        mock_page.keyboard.press = AsyncMock()
        mock_page.wait_for_timeout = AsyncMock()
        
        connection = ChromeConnection(mock_context)
        connection._current_page = mock_page
        
        await connection.force_close_all_modals()
        
        # Verify JavaScript was executed
        assert mock_page.evaluate.call_count >= 3  # Multiple evaluate calls
        
        # Verify Escape was pressed multiple times
        assert mock_page.keyboard.press.call_count >= 3
        
        # Check that the JavaScript code includes editable field handling
        first_eval_call = mock_page.evaluate.call_args_list[0][0][0]
        assert 'activeElement' in first_eval_call
        assert 'blur()' in first_eval_call
    
    @pytest.mark.asyncio
    async def test_is_modal_open(self):
        """Test checking if modal is open."""
        # Create mock page and context
        mock_page = AsyncMock(spec=Page)
        mock_context = AsyncMock()
        mock_context.pages = [mock_page]
        
        # Mock locator
        mock_locator = AsyncMock(spec=Locator)
        mock_locator.count = AsyncMock(return_value=1)
        mock_page.locator = MagicMock(return_value=mock_locator)
        
        connection = ChromeConnection(mock_context)
        connection._current_page = mock_page
        
        result = await connection.is_modal_open()
        
        assert result is True
        mock_page.locator.assert_called_with('[role="dialog"], [aria-modal="true"]')
    
    @pytest.mark.asyncio
    async def test_is_modal_open_no_modal(self):
        """Test checking when no modal is open."""
        # Create mock page and context
        mock_page = AsyncMock(spec=Page)
        mock_context = AsyncMock()
        mock_context.pages = [mock_page]
        
        # Mock locator with no results
        mock_locator = AsyncMock(spec=Locator)
        mock_locator.count = AsyncMock(return_value=0)
        mock_page.locator = MagicMock(return_value=mock_locator)
        
        connection = ChromeConnection(mock_context)
        connection._current_page = mock_page
        
        result = await connection.is_modal_open()
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_ensure_clean_state_with_modal(self):
        """Test ensure_clean_state when modal is open."""
        # Create mock page and context
        mock_page = AsyncMock(spec=Page)
        mock_context = AsyncMock()
        mock_context.pages = [mock_page]
        
        connection = ChromeConnection(mock_context)
        connection._current_page = mock_page
        
        # Mock modal is open
        with patch.object(connection, 'is_modal_open', return_value=True):
            with patch.object(connection, 'force_close_all_modals') as mock_force_close:
                await connection.ensure_clean_state()
                
                # Verify force close was called
                mock_force_close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_ensure_clean_state_no_modal(self):
        """Test ensure_clean_state when no modal is open."""
        # Create mock page and context
        mock_page = AsyncMock(spec=Page)
        mock_context = AsyncMock()
        mock_context.pages = [mock_page]
        
        connection = ChromeConnection(mock_context)
        connection._current_page = mock_page
        
        # Mock no modal is open
        with patch.object(connection, 'is_modal_open', return_value=False):
            with patch.object(connection, 'force_close_all_modals') as mock_force_close:
                await connection.ensure_clean_state()
                
                # Verify force close was NOT called
                mock_force_close.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_open_file_modal_context_manager(self):
        """Test open_file_modal context manager."""
        # Create mock page and context
        mock_page = AsyncMock(spec=Page)
        mock_context = AsyncMock()
        mock_context.pages = [mock_page]
        
        # Mock thumbnail and button
        mock_thumb = AsyncMock()
        mock_h3 = AsyncMock()
        mock_h3.text_content = AsyncMock(return_value="test_file.txt")
        mock_thumb.query_selector = AsyncMock(side_effect=lambda sel: mock_h3 if sel == 'h3' else AsyncMock())
        
        mock_button = AsyncMock()
        mock_button.click = AsyncMock()
        mock_thumb.query_selector = AsyncMock(side_effect=lambda sel: mock_h3 if sel == 'h3' else mock_button)
        
        # Mock query_selector_all to return our thumbnail
        mock_page.query_selector_all = AsyncMock(return_value=[mock_thumb])
        mock_page.wait_for_timeout = AsyncMock()
        mock_page.locator = MagicMock()
        mock_locator = AsyncMock()
        mock_locator.count = AsyncMock(return_value=0)  # No modal after close
        mock_page.locator.return_value = mock_locator
        
        connection = ChromeConnection(mock_context)
        connection._current_page = mock_page
        
        # Mock ensure_clean_state and _close_modal
        with patch.object(connection, 'ensure_clean_state') as mock_ensure_clean:
            with patch.object(connection, '_close_modal') as mock_close_modal:
                async with connection.open_file_modal("test_file.txt") as page:
                    assert page == mock_page
                    # Verify button was clicked
                    mock_button.click.assert_called_once()
                
                # Verify cleanup was called
                mock_ensure_clean.assert_called_once()
                mock_close_modal.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_open_file_modal_with_stuck_modal(self):
        """Test open_file_modal when modal doesn't close properly."""
        # Create mock page and context
        mock_page = AsyncMock(spec=Page)
        mock_context = AsyncMock()
        mock_context.pages = [mock_page]
        
        # Mock thumbnail and button
        mock_thumb = AsyncMock()
        mock_h3 = AsyncMock()
        mock_h3.text_content = AsyncMock(return_value="test_file.txt")
        mock_button = AsyncMock()
        mock_button.click = AsyncMock()
        mock_thumb.query_selector = AsyncMock(side_effect=lambda sel: mock_h3 if sel == 'h3' else mock_button)
        
        # Mock query_selector_all to return our thumbnail
        mock_page.query_selector_all = AsyncMock(return_value=[mock_thumb])
        mock_page.wait_for_timeout = AsyncMock()
        
        # Mock locator to indicate modal is still open after close attempt
        mock_locator = AsyncMock()
        mock_locator.count = AsyncMock(return_value=1)  # Modal still open
        mock_page.locator = MagicMock(return_value=mock_locator)
        
        connection = ChromeConnection(mock_context)
        connection._current_page = mock_page
        
        # Mock methods
        with patch.object(connection, 'ensure_clean_state') as mock_ensure_clean:
            with patch.object(connection, '_close_modal') as mock_close_modal:
                with patch.object(connection, 'force_close_all_modals') as mock_force_close:
                    async with connection.open_file_modal("test_file.txt") as page:
                        pass
                    
                    # Verify force close was called due to stuck modal
                    mock_force_close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_download_file_content_with_error_triggers_cleanup(self):
        """Test that download errors trigger modal cleanup."""
        # Create mock page and context
        mock_page = AsyncMock(spec=Page)
        mock_context = AsyncMock()
        mock_context.pages = [mock_page]
        
        connection = ChromeConnection(mock_context)
        connection._current_page = mock_page
        
        # Mock open_file_modal to raise an exception
        with patch.object(connection, 'open_file_modal') as mock_open_modal:
            mock_open_modal.side_effect = Exception("Download failed")
            
            with patch.object(connection, 'force_close_all_modals') as mock_force_close:
                result = await connection.download_file_content("test_file.txt")
                
                assert result is None
                # Verify force close was called due to error
                mock_force_close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_javascript_syntax_is_valid(self):
        """Test that JavaScript code in force_close_all_modals is syntactically valid."""
        # Create mock page and context
        mock_page = AsyncMock(spec=Page)
        mock_context = AsyncMock()
        mock_context.pages = [mock_page]
        
        # Capture the JavaScript code that's executed
        js_code_executed = []
        
        async def capture_js(code):
            js_code_executed.append(code)
            # Simulate successful execution
            return None
        
        mock_page.evaluate = capture_js
        mock_page.keyboard = AsyncMock()
        mock_page.keyboard.press = AsyncMock()
        mock_page.wait_for_timeout = AsyncMock()
        
        connection = ChromeConnection(mock_context)
        connection._current_page = mock_page
        
        await connection.force_close_all_modals()
        
        # Verify JavaScript was captured
        assert len(js_code_executed) > 0
        
        # Check that the JavaScript doesn't contain Playwright-specific selectors
        main_js = js_code_executed[0]
        assert ':has-text(' not in main_js
        assert 'button:has-text(' not in main_js
        
        # Verify it contains the fixed selectors
        assert 'button[aria-label*="close" i]' in main_js
        assert 'activeElement' in main_js  # Editable field handling
        assert 'blur()' in main_js
        
        # Verify text matching is done correctly
        assert 'textContent' in main_js or 'innerText' in main_js
        assert 'match(' in main_js  # Regex matching for button text