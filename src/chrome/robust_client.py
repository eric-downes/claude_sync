"""
Robust Chrome DevTools Protocol client with reconnection and state management.
"""
import json
import time
import logging
from typing import Any, Dict, List, Optional

import requests
import websocket

from .exceptions import (
    ChromeConnectionError,
    ChromeNotFoundError,
    ChromePageNotFoundError,
    ChromeWebSocketError,
)

logger = logging.getLogger(__name__)


class RobustChromeClient:
    """Robust client for Chrome DevTools with auto-reconnection and page state management."""
    
    def __init__(self, host: str = "localhost", port: int = 9222, timeout: int = 30):
        """Initialize the robust Chrome client."""
        self.host = host
        self.port = port
        self.timeout = timeout
        self._ws: Optional[websocket.WebSocket] = None
        self._command_id = 0
        self._current_page: Optional[Dict[str, Any]] = None
        self._domains_enabled = set()
    
    @property
    def base_url(self) -> str:
        """Get the base URL for Chrome DevTools."""
        return f"http://{self.host}:{self.port}"
    
    def get_pages(self) -> List[Dict[str, Any]]:
        """Get list of all pages from Chrome."""
        try:
            response = requests.get(
                f"{self.base_url}/json",
                timeout=self.timeout
            )
            response.raise_for_status()
            pages = response.json()
            # Filter to only actual pages (not workers, extensions, etc.)
            return [p for p in pages if p.get("type") == "page"]
        except requests.exceptions.ConnectionError:
            raise ChromeNotFoundError(
                f"Chrome not found at {self.host}:{self.port}. "
                "Make sure Chrome is running with --remote-debugging-port flag"
            )
        except Exception as e:
            raise ChromeConnectionError(f"Failed to get pages: {e}")
    
    def create_new_tab(self, url: str = "about:blank") -> Dict[str, Any]:
        """Create a new tab and navigate to URL."""
        try:
            response = requests.put(f"{self.base_url}/json/new?{url}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise ChromeConnectionError(f"Failed to create new tab: {e}")
    
    def close_tab(self, tab_id: str) -> None:
        """Close a specific tab."""
        try:
            requests.delete(f"{self.base_url}/json/close/{tab_id}")
        except Exception:
            pass  # Tab might already be closed
    
    def connect_to_page(self, page: Optional[Dict[str, Any]] = None) -> None:
        """Connect to a specific page or the first available one."""
        # Close existing connection if any
        if self._ws:
            try:
                self._ws.close()
            except Exception:
                pass
            self._ws = None
            self._domains_enabled.clear()
        
        # Get page to connect to
        if page is None:
            pages = self.get_pages()
            if not pages:
                raise ChromePageNotFoundError("No pages available in Chrome")
            page = pages[0]
        
        self._current_page = page
        
        # Connect via WebSocket
        ws_url = page.get("webSocketDebuggerUrl")
        if not ws_url:
            raise ChromeConnectionError("Page does not have WebSocket URL")
        
        try:
            self._ws = websocket.create_connection(ws_url, timeout=self.timeout)
            logger.info(f"Connected to page: {page.get('url', 'Unknown')}")
            
            # Enable essential domains
            self._enable_domains()
            
            # Check page state
            self._ensure_page_loaded()
            
        except Exception as e:
            raise ChromeWebSocketError(f"Failed to connect to page: {e}")
    
    def _enable_domains(self) -> None:
        """Enable essential Chrome DevTools domains."""
        domains = ["Page", "Runtime", "DOM", "Network"]
        for domain in domains:
            if domain not in self._domains_enabled:
                try:
                    self.send_command(f"{domain}.enable", {})
                    self._domains_enabled.add(domain)
                except Exception as e:
                    logger.warning(f"Failed to enable {domain}: {e}")
    
    def _ensure_page_loaded(self, max_attempts: int = 10) -> None:
        """Ensure the page is properly loaded with a document body."""
        for attempt in range(max_attempts):
            try:
                # Check document state
                state_json = self.evaluate_expression("""
                    JSON.stringify({
                        readyState: document.readyState,
                        hasBody: !!document.body,
                        bodyChildren: document.body ? document.body.children.length : 0,
                        url: window.location.href
                    })
                """)
                
                if state_json:
                    state = json.loads(state_json) if isinstance(state_json, str) else state_json
                    logger.debug(f"Page state (attempt {attempt + 1}): {state}")
                    
                    if state.get("hasBody") and state.get("bodyChildren", 0) > 0:
                        logger.info("Page loaded successfully")
                        return
                    
                    if state.get("readyState") == "complete" and not state.get("hasBody"):
                        # Page says it's complete but has no body - might need reload
                        logger.warning("Page reports complete but has no body, reloading...")
                        self.send_command("Page.reload", {})
                        time.sleep(3)
                        continue
                else:
                    logger.warning(f"No state returned on attempt {attempt + 1}")
                
            except Exception as e:
                logger.warning(f"Error checking page state: {e}")
            
            time.sleep(1)
        
        logger.warning("Page may not be fully loaded after all attempts")
    
    def send_command(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send a command to Chrome and wait for response."""
        if not self._ws:
            # Try to reconnect
            if self._current_page:
                self.connect_to_page(self._current_page)
            else:
                raise ChromeConnectionError("No WebSocket connection")
        
        self._command_id += 1
        message = {
            "id": self._command_id,
            "method": method,
            "params": params or {}
        }
        
        try:
            self._ws.send(json.dumps(message))
            
            # Wait for response with matching ID
            while True:
                response = json.loads(self._ws.recv())
                
                # Handle events (no ID)
                if "method" in response and "params" in response:
                    logger.debug(f"Received event: {response['method']}")
                    continue
                
                # Check if this is our response
                if response.get("id") == self._command_id:
                    if "error" in response:
                        raise ChromeWebSocketError(
                            f"Command error: {response['error'].get('message', 'Unknown error')}"
                        )
                    return response
                    
        except websocket.WebSocketException as e:
            # Connection lost, try to reconnect once
            logger.warning(f"WebSocket error: {e}, attempting reconnect...")
            self._ws = None
            if self._current_page:
                self.connect_to_page(self._current_page)
                # Retry the command
                return self.send_command(method, params)
            raise ChromeWebSocketError(f"WebSocket error: {e}")
    
    def navigate_and_wait(self, url: str, wait_time: int = 3) -> None:
        """Navigate to URL and wait for page to load."""
        logger.info(f"Navigating to {url}")
        result = self.send_command("Page.navigate", {"url": url})
        frame_id = result.get("frameId")
        logger.debug(f"Navigation started, frame ID: {frame_id}")
        
        # Wait for initial load
        time.sleep(wait_time)
        
        # Ensure page is loaded
        self._ensure_page_loaded()
    
    def evaluate_expression(self, expression: str) -> Any:
        """Evaluate JavaScript expression and return the result."""
        result = self.send_command("Runtime.evaluate", {
            "expression": expression
        })
        
        # Check for errors
        if "exceptionDetails" in result:
            logger.error(f"JavaScript error: {result['exceptionDetails']}")
            return None
        
        # Navigate through the nested result structure
        if "result" in result:
            inner_result = result["result"]
            if "result" in inner_result:
                # Double-nested result (seems to be the case)
                result_obj = inner_result["result"]
            else:
                result_obj = inner_result
        else:
            logger.warning(f"Unexpected result structure: {result}")
            return None
        
        if result_obj.get("type") == "undefined":
            return None
        
        # Get the value
        if "value" in result_obj:
            value = result_obj["value"]
            
            # If it's a JSON string, try to parse it
            if result_obj.get("type") == "string" and isinstance(value, str):
                if (value.startswith("{") and value.endswith("}")) or \
                   (value.startswith("[") and value.endswith("]")):
                    try:
                        return json.loads(value)
                    except json.JSONDecodeError:
                        pass
            
            return value
        else:
            # For complex objects without direct value
            logger.debug(f"No direct value in result object: {result_obj}")
            return None
    
    def get_page_content(self) -> Dict[str, Any]:
        """Get comprehensive page content information."""
        content = self.evaluate_expression("""
            JSON.stringify({
                url: window.location.href,
                title: document.title,
                readyState: document.readyState,
                hasBody: !!document.body,
                bodyChildren: document.body ? document.body.children.length : 0,
                bodyText: document.body ? document.body.innerText.substring(0, 1000) : '',
                bodyHTML: document.body ? document.body.innerHTML.substring(0, 1000) : '',
                forms: document.querySelectorAll('form').length,
                inputs: document.querySelectorAll('input').length,
                buttons: document.querySelectorAll('button').length,
                links: document.querySelectorAll('a').length,
                images: document.querySelectorAll('img').length
            })
        """)
        
        # Return default values if evaluation failed
        if content is None:
            return {
                "url": "unknown",
                "title": "unknown",
                "readyState": "unknown",
                "hasBody": False,
                "bodyChildren": 0,
                "bodyText": "",
                "bodyHTML": "",
                "forms": 0,
                "inputs": 0,
                "buttons": 0,
                "links": 0,
                "images": 0
            }
        
        return content
    
    def close(self) -> None:
        """Close the WebSocket connection."""
        if self._ws:
            try:
                self._ws.close()
            except Exception:
                pass
            self._ws = None
            self._domains_enabled.clear()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()