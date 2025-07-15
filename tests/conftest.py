"""
Shared pytest fixtures and configuration for claude-sync tests.
"""
import pytest
import json
from unittest.mock import Mock, MagicMock
import asyncio


@pytest.fixture
def mock_chrome_pages_response():
    """Mock response from Chrome's /json endpoint."""
    return [
        {
            "id": "1",
            "url": "https://claude.ai/projects",
            "title": "Projects - Claude",
            "type": "page",
            "webSocketDebuggerUrl": "ws://localhost:9222/devtools/page/1"
        },
        {
            "id": "2",
            "url": "https://stripe.com/iframe",
            "title": "Stripe",
            "type": "iframe",
            "webSocketDebuggerUrl": "ws://localhost:9222/devtools/page/2"
        }
    ]


@pytest.fixture
def mock_websocket():
    """Mock WebSocket connection."""
    ws = MagicMock()
    ws.recv.return_value = json.dumps({
        "id": 1,
        "result": {
            "result": {
                "value": {"status": "ok"}
            }
        }
    })
    return ws


@pytest.fixture
def mock_projects_data():
    """Mock project data extracted from Claude."""
    return [
        {
            "name": "Test Project 1",
            "url": "https://claude.ai/project/test-id-1",
            "id": "test-id-1"
        },
        {
            "name": "Test Project 2",
            "url": "https://claude.ai/project/test-id-2",
            "id": "test-id-2"
        }
    ]


@pytest.fixture
def mock_knowledge_files():
    """Mock knowledge files from a project."""
    return [
        {
            "name": "README.md",
            "type": "markdown",
            "content": "# Test Project\n\nThis is a test project.",
            "hash": "abc123"
        },
        {
            "name": "main.py",
            "type": "python",
            "content": "def main():\n    print('Hello, World!')",
            "hash": "def456"
        }
    ]


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()