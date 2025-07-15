"""
Unit tests for ChromeClient class.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import json
import requests

from src.chrome.client import ChromeClient
from src.chrome.exceptions import (
    ChromeConnectionError,
    ChromeNotFoundError,
    ChromePageNotFoundError,
    ChromeWebSocketError,
)


class TestChromeClient:
    """Test ChromeClient functionality."""
    
    def test_init_default_values(self):
        """Test ChromeClient initializes with default values."""
        client = ChromeClient()
        assert client.host == "localhost"
        assert client.port == 9222
        assert client.timeout == 30
    
    def test_init_custom_values(self):
        """Test ChromeClient initializes with custom values."""
        client = ChromeClient(host="127.0.0.1", port=9333, timeout=60)
        assert client.host == "127.0.0.1"
        assert client.port == 9333
        assert client.timeout == 60
    
    @patch('requests.get')
    def test_get_pages_success(self, mock_get, mock_chrome_pages_response):
        """Test getting pages from Chrome successfully."""
        mock_get.return_value.json.return_value = mock_chrome_pages_response
        mock_get.return_value.raise_for_status.return_value = None
        
        client = ChromeClient()
        pages = client.get_pages()
        
        assert len(pages) == 2
        assert pages[0]["url"] == "https://claude.ai/projects"
        mock_get.assert_called_once_with("http://localhost:9222/json", timeout=30)
    
    @patch('requests.get')
    def test_get_pages_connection_error(self, mock_get):
        """Test handling connection error when getting pages."""
        mock_get.side_effect = requests.ConnectionError("Connection refused")
        
        client = ChromeClient()
        with pytest.raises(ChromeNotFoundError) as exc_info:
            client.get_pages()
        
        assert "Chrome is not running" in str(exc_info.value)
    
    @patch('requests.get')
    def test_find_claude_page_success(self, mock_get, mock_chrome_pages_response):
        """Test finding Claude page successfully."""
        mock_get.return_value.json.return_value = mock_chrome_pages_response
        mock_get.return_value.raise_for_status.return_value = None
        
        client = ChromeClient()
        page = client.find_claude_page()
        
        assert page is not None
        assert page["url"] == "https://claude.ai/projects"
        assert "stripe" not in page["url"]
    
    @patch('requests.get')
    def test_find_claude_page_not_found(self, mock_get):
        """Test handling when Claude page is not found."""
        mock_get.return_value.json.return_value = [
            {
                "id": "1",
                "url": "https://google.com",
                "type": "page",
                "webSocketDebuggerUrl": "ws://localhost:9222/devtools/page/1"
            }
        ]
        mock_get.return_value.raise_for_status.return_value = None
        
        client = ChromeClient()
        with pytest.raises(ChromePageNotFoundError) as exc_info:
            client.find_claude_page()
        
        assert "No Claude.ai page found" in str(exc_info.value)
    
    @patch('websocket.create_connection')
    @patch('requests.get')
    def test_connect_to_page_success(self, mock_get, mock_create_connection, 
                                   mock_chrome_pages_response):
        """Test connecting to a page via WebSocket."""
        mock_get.return_value.json.return_value = mock_chrome_pages_response
        mock_get.return_value.raise_for_status.return_value = None
        
        # Create a more sophisticated mock that tracks command IDs
        mock_ws = MagicMock()
        command_id = 0
        
        def mock_recv():
            nonlocal command_id
            command_id += 1
            return json.dumps({"id": command_id, "result": {}})
        
        mock_ws.recv.side_effect = mock_recv
        mock_create_connection.return_value = mock_ws
        
        client = ChromeClient()
        ws = client.connect_to_page()
        
        assert ws is not None
        assert ws == mock_ws
        mock_create_connection.assert_called_once_with(
            "ws://localhost:9222/devtools/page/1"
        )
    
    @patch('websocket.create_connection')
    @patch('requests.get')
    def test_connect_to_page_websocket_error(self, mock_get, mock_create_connection,
                                           mock_chrome_pages_response):
        """Test handling WebSocket connection error."""
        mock_get.return_value.json.return_value = mock_chrome_pages_response
        mock_get.return_value.raise_for_status.return_value = None
        mock_create_connection.side_effect = Exception("WebSocket error")
        
        client = ChromeClient()
        with pytest.raises(ChromeWebSocketError) as exc_info:
            client.connect_to_page()
        
        assert "Failed to connect to Chrome page" in str(exc_info.value)
    
    @patch('websocket.create_connection')
    def test_send_command_success(self, mock_create_connection):
        """Test sending a command to Chrome successfully."""
        mock_ws = MagicMock()
        mock_ws.recv.return_value = json.dumps({
            "id": 1,
            "result": {"value": "test_result"}
        })
        
        client = ChromeClient()
        client._ws = mock_ws
        client._command_id = 0
        
        result = client.send_command("Runtime.evaluate", {"expression": "1+1"})
        
        assert result == {"value": "test_result"}
        mock_ws.send.assert_called_once()
        sent_data = json.loads(mock_ws.send.call_args[0][0])
        assert sent_data["method"] == "Runtime.evaluate"
        assert sent_data["params"] == {"expression": "1+1"}
        assert sent_data["id"] == 1
    
    def test_send_command_no_connection(self):
        """Test sending command without WebSocket connection."""
        client = ChromeClient()
        
        with pytest.raises(ChromeConnectionError) as exc_info:
            client.send_command("Runtime.evaluate", {"expression": "1+1"})
        
        assert "No WebSocket connection" in str(exc_info.value)
    
    @patch('websocket.create_connection')
    @patch('requests.get')
    def test_navigate_to_url(self, mock_get, mock_create_connection,
                           mock_chrome_pages_response):
        """Test navigating to a URL."""
        mock_get.return_value.json.return_value = mock_chrome_pages_response
        mock_get.return_value.raise_for_status.return_value = None
        
        # Create a mock that handles multiple commands
        mock_ws = MagicMock()
        command_id = 0
        
        def mock_recv():
            nonlocal command_id
            command_id += 1
            return json.dumps({"id": command_id, "result": {}})
        
        mock_ws.recv.side_effect = mock_recv
        mock_create_connection.return_value = mock_ws
        
        client = ChromeClient()
        client.connect_to_page()
        client.navigate_to("https://claude.ai/projects")
        
        # Verify navigation command was sent
        calls = [json.loads(call[0][0]) for call in mock_ws.send.call_args_list]
        nav_call = next(c for c in calls if c.get("method") == "Page.navigate")
        assert nav_call["params"]["url"] == "https://claude.ai/projects"
    
    @patch('websocket.create_connection')
    def test_close_connection(self, mock_create_connection):
        """Test closing WebSocket connection."""
        mock_ws = MagicMock()
        
        client = ChromeClient()
        client._ws = mock_ws
        client.close()
        
        mock_ws.close.assert_called_once()
        assert client._ws is None
    
    def test_context_manager(self):
        """Test ChromeClient as context manager."""
        with patch('requests.get') as mock_get, \
             patch('websocket.create_connection') as mock_create_connection:
            
            mock_get.return_value.json.return_value = [{
                "id": "1",
                "url": "https://claude.ai",
                "type": "page",
                "webSocketDebuggerUrl": "ws://localhost:9222/devtools/page/1"
            }]
            mock_get.return_value.raise_for_status.return_value = None
            
            # Setup mock with proper recv responses
            mock_ws = MagicMock()
            command_id = 0
            
            def mock_recv():
                nonlocal command_id
                command_id += 1
                return json.dumps({"id": command_id, "result": {}})
            
            mock_ws.recv.side_effect = mock_recv
            mock_create_connection.return_value = mock_ws
            
            with ChromeClient() as client:
                assert client._ws is not None
            
            mock_ws.close.assert_called_once()