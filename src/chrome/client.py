"""
Chrome DevTools Protocol client for interacting with Chrome browser.
"""
import json
import time
from typing import Any, Dict, List, Optional

import requests
import websocket

from .exceptions import (
    ChromeConnectionError,
    ChromeNotFoundError,
    ChromePageNotFoundError,
    ChromeWebSocketError,
)


class ChromeClient:
    """Client for interacting with Chrome via DevTools Protocol."""

    def __init__(self, host: str = "localhost", port: int = 9222, timeout: int = 30):
        """
        Initialize Chrome client.

        Args:
            host: Chrome debug host
            port: Chrome debug port
            timeout: Request timeout in seconds
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self._ws: Optional[websocket.WebSocket] = None
        self._command_id = 0

    def get_pages(self) -> List[Dict[str, Any]]:
        """
        Get list of all pages from Chrome.

        Returns:
            List of page dictionaries

        Raises:
            ChromeNotFoundError: If Chrome is not running
            ChromeConnectionError: If connection fails
        """
        try:
            response = requests.get(
                f"http://{self.host}:{self.port}/json",
                timeout=self.timeout
            )
            response.raise_for_status()
            pages: List[Dict[str, Any]] = response.json()
            return pages
        except requests.ConnectionError as e:
            raise ChromeNotFoundError(
                f"Chrome is not running on {self.host}:{self.port}. "
                "Please start Chrome with --remote-debugging-port=9222"
            ) from e
        except Exception as e:
            raise ChromeConnectionError(f"Failed to get pages: {str(e)}") from e

    def find_claude_page(self) -> Dict[str, Any]:
        """
        Find the main Claude.ai page (not iframe).

        Returns:
            Page dictionary for Claude page

        Raises:
            ChromePageNotFoundError: If Claude page not found
        """
        pages = self.get_pages()
        
        # Debug: show what we found
        claude_related = []
        for page in pages:
            url = page.get("url", "")
            if "claude.ai" in url:
                claude_related.append(f"{page.get('type', 'unknown')}: {url}")

        for page in pages:
            url = page.get("url", "")
            page_type = page.get("type", "")

            # Look for main Claude page, not Stripe iframe
            if "claude.ai" in url and "stripe" not in url and page_type == "page":
                return page

        # Enhanced error message with debug info
        error_msg = "No Claude.ai page found. Please navigate to claude.ai"
        if claude_related:
            error_msg += f"\nFound {len(claude_related)} Claude-related pages, but none were the main page:"
            for cr in claude_related:
                error_msg += f"\n  - {cr}"
        else:
            error_msg += f"\nNo Claude.ai pages found among {len(pages)} open tabs"
        
        raise ChromePageNotFoundError(error_msg)

    def connect_to_page(self, page: Optional[Dict[str, Any]] = None) -> websocket.WebSocket:
        """
        Connect to a Chrome page via WebSocket.

        Args:
            page: Page dictionary to connect to. If None, finds Claude page.

        Returns:
            WebSocket connection

        Raises:
            ChromeWebSocketError: If connection fails
        """
        if page is None:
            page = self.find_claude_page()

        ws_url = page.get("webSocketDebuggerUrl")
        if not ws_url:
            raise ChromeWebSocketError("Page has no WebSocket URL")

        try:
            self._ws = websocket.create_connection(ws_url)
            self._enable_domains()
            return self._ws
        except Exception as e:
            raise ChromeWebSocketError(
                f"Failed to connect to Chrome page: {str(e)}"
            ) from e

    def _enable_domains(self) -> None:
        """Enable necessary Chrome DevTools domains."""
        if not self._ws:
            return

        domains = ["Page", "Runtime", "DOM"]
        for domain in domains:
            self.send_command(f"{domain}.enable", {})

    def send_command(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send a command to Chrome and wait for response.

        Args:
            method: Chrome DevTools method name
            params: Method parameters

        Returns:
            Response result

        Raises:
            ChromeConnectionError: If no WebSocket connection
            ChromeWebSocketError: If command fails
        """
        if not self._ws:
            raise ChromeConnectionError("No WebSocket connection")

        self._command_id += 1
        command = {
            "id": self._command_id,
            "method": method,
            "params": params
        }

        try:
            self._ws.send(json.dumps(command))

            # Wait for response with matching ID
            while True:
                response = json.loads(self._ws.recv())
                if response.get("id") == self._command_id:
                    if "error" in response:
                        raise ChromeWebSocketError(
                            f"Command failed: {response['error']}"
                        )
                    result: Dict[str, Any] = response.get("result", {})
                    return result

        except websocket.WebSocketException as e:
            raise ChromeWebSocketError(f"WebSocket error: {str(e)}") from e
        except Exception as e:
            raise ChromeWebSocketError(f"Command failed: {str(e)}") from e

    def navigate_to(self, url: str) -> None:
        """
        Navigate to a URL.

        Args:
            url: URL to navigate to
        """
        self.send_command("Page.navigate", {"url": url})
        time.sleep(2)  # Give page time to load

    def close(self) -> None:
        """Close WebSocket connection."""
        if self._ws:
            self._ws.close()
            self._ws = None

    def __enter__(self) -> "ChromeClient":
        """Context manager entry."""
        self.connect_to_page()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.close()
