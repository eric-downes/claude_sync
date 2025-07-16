"""
Fixed unit tests for ProjectExtractor with both link-based and update-based extraction.
"""
from unittest.mock import Mock, patch
import pytest

from src.chrome.client import ChromeClient
from src.chrome.exceptions import ChromeWebSocketError, ProjectExtractionError
from src.extractors.models import Project
from src.extractors.projects import ProjectExtractor


class TestProjectExtractor:
    """Test ProjectExtractor with current implementation."""

    def test_init(self):
        """Test ProjectExtractor initialization."""
        mock_client = Mock(spec=ChromeClient)
        extractor = ProjectExtractor(mock_client)
        assert extractor.client == mock_client

    def test_navigate_to_projects_page_already_there(self):
        """Test when already on projects page."""
        mock_client = Mock(spec=ChromeClient)
        mock_client.send_command.return_value = {
            "result": {"value": "https://claude.ai/projects"}
        }
        
        extractor = ProjectExtractor(mock_client)
        extractor.navigate_to_projects_page()
        
        # Should check URL but not navigate
        mock_client.send_command.assert_called_once_with(
            "Runtime.evaluate",
            {"expression": "window.location.href"}
        )

    @patch('time.sleep')
    def test_navigate_to_projects_page_from_elsewhere(self, mock_sleep):
        """Test navigating from a different page."""
        mock_client = Mock(spec=ChromeClient)
        mock_client.send_command.side_effect = [
            {"result": {"value": "https://claude.ai/chat/123"}},  # Current URL
            {"frameId": "123"}  # Navigation response
        ]
        
        extractor = ProjectExtractor(mock_client)
        extractor.navigate_to_projects_page()
        
        # Should navigate
        assert mock_client.send_command.call_count == 2
        mock_client.send_command.assert_any_call(
            "Page.navigate",
            {"url": "https://claude.ai/projects"}
        )

    @patch('time.sleep')
    def test_wait_for_projects_loaded_success(self, mock_sleep):
        """Test waiting for projects to load successfully."""
        mock_client = Mock(spec=ChromeClient)
        mock_client.send_command.return_value = {"result": {"value": True}}
        
        extractor = ProjectExtractor(mock_client)
        extractor._wait_for_projects_loaded(timeout=5)
        
        # Should check for loading state
        mock_client.send_command.assert_called()

    @patch('time.sleep')
    @patch('time.time')
    def test_wait_for_projects_loaded_timeout(self, mock_time, mock_sleep):
        """Test timeout when projects don't load."""
        mock_client = Mock(spec=ChromeClient)
        mock_client.send_command.return_value = {"result": {"value": False}}
        
        # Simulate timeout
        mock_time.side_effect = [0, 1, 2, 3, 4, 5, 6]
        
        extractor = ProjectExtractor(mock_client)
        with pytest.raises(Exception) as exc_info:
            extractor._wait_for_projects_loaded(timeout=5)
        
        assert "Timeout" in str(exc_info.value)

    def test_extract_project_links_success(self):
        """Test successful link-based extraction."""
        mock_client = Mock(spec=ChromeClient)
        mock_client.send_command.return_value = {
            "result": {
                "value": [
                    {
                        "id": "proj-123",
                        "name": "Test Project",
                        "url": "https://claude.ai/project/proj-123",
                        "updated": "Updated 2 days ago"
                    },
                    {
                        "id": "proj-456",
                        "name": "Another Project",
                        "url": "https://claude.ai/project/proj-456",
                        "updated": "Updated 1 week ago"
                    }
                ]
            }
        }
        
        extractor = ProjectExtractor(mock_client)
        projects = extractor._extract_project_links()
        
        assert len(projects) == 2
        assert projects[0]["id"] == "proj-123"
        assert projects[1]["name"] == "Another Project"

    def test_extract_project_data_success(self):
        """Test successful update-based extraction."""
        mock_client = Mock(spec=ChromeClient)
        mock_client.send_command.return_value = {
            "result": {
                "value": [
                    {
                        "name": "Math Project",
                        "id": "proj-math",
                        "url": "https://claude.ai/project/proj-math",
                        "updated": "Updated 3 days ago",
                        "description": "A project about mathematics"
                    }
                ]
            }
        }
        
        extractor = ProjectExtractor(mock_client)
        projects = extractor._extract_project_data()
        
        assert len(projects) == 1
        assert projects[0]["name"] == "Math Project"
        assert projects[0]["description"] == "A project about mathematics"

    @patch('time.sleep')
    def test_extract_projects_combines_both_methods(self, mock_sleep):
        """Test that extract_projects uses both extraction methods."""
        mock_client = Mock(spec=ChromeClient)
        
        # Mock responses for the full flow
        def mock_send_command(method, params):
            if method == "Runtime.evaluate":
                expr = params.get("expression", "")
                
                # URL check
                if "window.location.href" in expr:
                    return {"result": {"value": "https://claude.ai/projects"}}
                
                # Projects loaded check
                elif "hasNewButton" in expr or "hasProjectCards" in expr:
                    return {"result": {"value": True}}
                
                # Scroll check
                elif "scrollHeight" in expr:
                    return {"result": {"value": {"needsScroll": False}}}
                
                # Link extraction (first method)
                elif "a[href*=\"/project/\"]" in expr:
                    return {
                        "result": {
                            "value": [
                                {
                                    "id": "123-uuid",
                                    "name": "Link Project",
                                    "url": "https://claude.ai/project/123-uuid",
                                    "updated": "Updated 1 day ago"
                                }
                            ]
                        }
                    }
                
                # Update extraction (second method)
                elif "updateElements" in expr or "projectContainers" in expr:
                    return {
                        "result": {
                            "value": [
                                {
                                    "id": "proj-update-based",
                                    "name": "Update Project",
                                    "url": "https://claude.ai/project/proj-update-based",
                                    "updated": "Updated 2 days ago"
                                }
                            ]
                        }
                    }
            
            return {}
        
        mock_client.send_command.side_effect = mock_send_command
        
        extractor = ProjectExtractor(mock_client)
        projects = extractor.extract_projects()
        
        # Should have projects from both methods
        assert len(projects) == 2
        project_names = {p.name for p in projects}
        assert "Link Project" in project_names
        assert "Update Project" in project_names

    @patch('time.sleep')
    def test_extract_projects_deduplicates_by_id(self, mock_sleep):
        """Test that duplicate project IDs are handled."""
        mock_client = Mock(spec=ChromeClient)
        
        def mock_send_command(method, params):
            if method == "Runtime.evaluate":
                expr = params.get("expression", "")
                
                if "window.location.href" in expr:
                    return {"result": {"value": "https://claude.ai/projects"}}
                elif "hasNewButton" in expr:
                    return {"result": {"value": True}}
                elif "scrollHeight" in expr:
                    return {"result": {"value": {"needsScroll": False}}}
                elif "a[href*=\"/project/\"]" in expr:
                    return {
                        "result": {
                            "value": [
                                {
                                    "id": "same-id",
                                    "name": "Project from Links",
                                    "url": "https://claude.ai/project/same-id",
                                    "updated": "Updated 1 day ago"
                                }
                            ]
                        }
                    }
                elif "updateElements" in expr:
                    return {
                        "result": {
                            "value": [
                                {
                                    "id": "same-id",
                                    "name": "Project from Updates",
                                    "url": "https://claude.ai/project/same-id",
                                    "updated": "Updated 1 day ago",
                                    "description": "With description"
                                }
                            ]
                        }
                    }
            return {}
        
        mock_client.send_command.side_effect = mock_send_command
        
        extractor = ProjectExtractor(mock_client)
        projects = extractor.extract_projects()
        
        # Should have only one project with the same ID
        assert len(projects) == 1
        # Should have the description from the update method
        assert projects[0].description == "With description"

    @patch('time.sleep')
    def test_extract_projects_handles_errors_with_retry(self, mock_sleep):
        """Test that extraction fails after max retries."""
        mock_client = Mock(spec=ChromeClient)
        
        def mock_send_command(method, params):
            if method == "Runtime.evaluate":
                expr = params.get("expression", "")
                
                if "window.location.href" in expr:
                    return {"result": {"value": "https://claude.ai/projects"}}
                elif "hasNewButton" in expr:
                    return {"result": {"value": True}}
                elif "scrollHeight" in expr:
                    return {"result": {"value": {"needsScroll": False}}}
                elif "a[href*=\"/project/\"]" in expr:
                    # Always fail to test retry exhaustion
                    raise ChromeWebSocketError("Network error")
                elif "updateElements" in expr or "projectContainers" in expr:
                    return {"result": {"value": []}}
            
            return {}
        
        mock_client.send_command.side_effect = mock_send_command
        
        extractor = ProjectExtractor(mock_client)
        
        # Should raise after exhausting retries
        with pytest.raises(ProjectExtractionError) as exc_info:
            extractor.extract_projects(retry_count=2)
        
        assert "Failed to extract projects after 2 attempts" in str(exc_info.value)
        assert "Network error" in str(exc_info.value)

    def test_extract_projects_filters_invalid_data(self):
        """Test that invalid project data is filtered out."""
        mock_client = Mock(spec=ChromeClient)
        
        def mock_send_command(method, params):
            if method == "Runtime.evaluate":
                expr = params.get("expression", "")
                
                if "window.location.href" in expr:
                    return {"result": {"value": "https://claude.ai/projects"}}
                elif "hasNewButton" in expr:
                    return {"result": {"value": True}}
                elif "scrollHeight" in expr:
                    return {"result": {"value": {"needsScroll": False}}}
                elif "a[href*=\"/project/\"]" in expr:
                    return {
                        "result": {
                            "value": [
                                # Valid project
                                {
                                    "id": "valid-id",
                                    "name": "Valid Project",
                                    "url": "https://claude.ai/project/valid-id"
                                },
                                # Missing ID
                                {
                                    "name": "No ID Project",
                                    "url": "https://claude.ai/project/missing"
                                },
                                # Missing name
                                {
                                    "id": "no-name",
                                    "url": "https://claude.ai/project/no-name"
                                },
                                # Missing URL
                                {
                                    "id": "no-url",
                                    "name": "No URL Project"
                                }
                            ]
                        }
                    }
                elif "updateElements" in expr:
                    return {"result": {"value": []}}
            
            return {}
        
        mock_client.send_command.side_effect = mock_send_command
        
        extractor = ProjectExtractor(mock_client)
        with patch('time.sleep'):
            projects = extractor.extract_projects()
        
        # Should only have the valid project
        assert len(projects) == 1
        assert projects[0].id == "valid-id"
        assert projects[0].name == "Valid Project"

    @patch('time.sleep')
    def test_scroll_and_load_all(self, mock_sleep):
        """Test scrolling functionality."""
        mock_client = Mock(spec=ChromeClient)
        
        # Simulate scroll needed and project count increasing
        scroll_responses = [
            {"result": {"value": {"needsScroll": True}}},  # Initial check
            {"result": {"value": 10}},  # First count
            {},  # Scroll action
            {"result": {"value": 15}},  # Second count (increased)
            {},  # Scroll action
            {"result": {"value": 20}},  # Third count (increased)
            {},  # Scroll action
            {"result": {"value": 20}},  # Fourth count (stable)
            {},  # Scroll action
            {"result": {"value": 20}},  # Fifth count (stable - will exit)
        ]
        
        mock_client.send_command.side_effect = scroll_responses
        
        extractor = ProjectExtractor(mock_client)
        extractor._scroll_and_load_all()
        
        # Should have called scroll multiple times
        assert mock_client.send_command.call_count >= 5