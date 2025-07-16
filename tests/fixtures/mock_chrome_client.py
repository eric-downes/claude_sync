"""
Mock Chrome client for testing.
"""
from typing import Any, Dict, List, Optional

from src.chrome.client import ChromeClient


class MockChromeClient(ChromeClient):
    """Mock Chrome client that returns predefined responses."""

    def __init__(self, projects_data: Optional[List[Dict[str, Any]]] = None):
        """
        Initialize mock client with optional project data.

        Args:
            projects_data: List of project dictionaries to return
        """
        # Don't call parent __init__ to avoid real connections
        self.host = "localhost"
        self.port = 9222
        self.timeout = 30
        self._ws = None
        self._command_id = 0

        # Default projects if none provided
        if projects_data is None:
            projects_data = [
                {
                    "name": "Test Project Alpha",
                    "description": "A comprehensive test project with full description",
                    "updated": "Updated 1 day ago",
                    "id": "proj-test-project-alpha",
                    "url": "https://claude.ai/project/proj-test-project-alpha"
                },
                {
                    "name": "Test Project Beta",
                    "description": None,
                    "updated": "Updated 3 days ago",
                    "id": "proj-test-project-beta",
                    "url": "https://claude.ai/project/proj-test-project-beta"
                },
                {
                    "name": "Test Project Gamma",
                    "description": "Mathematical research project",
                    "updated": "Updated 1 week ago",
                    "id": "proj-test-project-gamma",
                    "url": "https://claude.ai/project/proj-test-project-gamma"
                },
                {
                    "name": "Test Project Delta",
                    "description": "Machine learning experiments",
                    "updated": "Updated 2 weeks ago",
                    "id": "proj-test-project-delta",
                    "url": "https://claude.ai/project/proj-test-project-delta"
                },
                {
                    "name": "Test Project Epsilon",
                    "description": None,
                    "updated": "Updated 1 month ago",
                    "id": "proj-test-project-epsilon",
                    "url": "https://claude.ai/project/proj-test-project-epsilon"
                }
            ]

        self.projects_data = projects_data
        self.current_url = "https://claude.ai/projects"
        self.is_loaded = True
        self.call_history: List[Dict[str, Any]] = []

    def send_command(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Mock send_command that returns appropriate responses.

        Args:
            method: Chrome DevTools method name
            params: Method parameters

        Returns:
            Mock response based on the method
        """
        # Record the call
        self.call_history.append({"method": method, "params": params})

        if method == "Runtime.evaluate":
            expression = params.get("expression", "")

            # Check current URL
            if "window.location.href" in expression:
                return {"result": {"value": self.current_url}}

            # Check if projects loaded
            elif "hasNewButton" in expression or "hasProjectCards" in expression:
                return {"result": {"value": self.is_loaded}}

            # Extract projects (handle both old and new extraction logic)
            elif "updateElements" in expression or "projectContainers" in expression:
                return {"result": {"value": self.projects_data}}
            elif "clickable" in expression or "Updated" in expression:
                return {"result": {"value": self.projects_data}}
            
            # Scroll checks
            elif "scrollHeight" in expression and "clientHeight" in expression:
                return {"result": {"value": {
                    "scrollHeight": 1000,
                    "clientHeight": 1000,
                    "needsScroll": False,
                    "currentScroll": 0
                }}}
            
            # Count projects
            elif expression.strip().startswith("Array.from") and "length" in expression:
                return {"result": {"value": len(self.projects_data)}}

        elif method == "Page.navigate":
            self.current_url = params.get("url", "")
            return {"frameId": "123"}

        elif method == "Page.enable" or method == "Runtime.enable" or method == "DOM.enable":
            return {}

        # Default response
        return {"result": {}}

    def navigate_to(self, url: str) -> None:
        """Mock navigation."""
        self.current_url = url

    def close(self) -> None:
        """Mock close."""
        pass

    def __enter__(self) -> "MockChromeClient":
        """Mock context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Mock context manager exit."""
        pass


class FailingMockChromeClient(MockChromeClient):
    """Mock Chrome client that simulates failures."""

    def __init__(self, fail_after: int = 0, error_message: str = "Mock error"):
        """
        Initialize failing mock client.

        Args:
            fail_after: Number of successful calls before failing
            error_message: Error message to raise
        """
        super().__init__()
        self.fail_after = fail_after
        self.error_message = error_message
        self.call_count = 0

    def send_command(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Mock send_command that fails after specified calls."""
        self.call_count += 1

        if self.call_count > self.fail_after:
            from src.chrome.exceptions import ChromeWebSocketError
            raise ChromeWebSocketError(self.error_message)

        return super().send_command(method, params)
