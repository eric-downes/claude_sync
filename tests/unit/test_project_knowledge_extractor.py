"""
Unit tests for ProjectKnowledgeExtractor class.
"""
from unittest.mock import Mock, patch
import pytest

from src.chrome.client import ChromeClient
from src.chrome.exceptions import ChromeWebSocketError, ExtractionError
from src.extractors.models import Project, KnowledgeFile
from src.extractors.knowledge import ProjectKnowledgeExtractor


class TestProjectKnowledgeExtractor:
    """Test ProjectKnowledgeExtractor functionality."""

    def test_init(self):
        """Test ProjectKnowledgeExtractor initialization."""
        mock_client = Mock(spec=ChromeClient)
        extractor = ProjectKnowledgeExtractor(mock_client)
        assert extractor.client == mock_client

    def test_navigate_to_project(self):
        """Test navigating to a specific project."""
        mock_client = Mock(spec=ChromeClient)
        mock_client.send_command.return_value = {"frameId": "123"}
        
        project = Project(
            id="test-id",
            name="Test Project",
            url="https://claude.ai/project/test-id"
        )
        
        extractor = ProjectKnowledgeExtractor(mock_client)
        extractor.navigate_to_project(project)
        
        # Should navigate to the project URL
        mock_client.send_command.assert_called_with(
            "Page.navigate",
            {"url": "https://claude.ai/project/test-id"}
        )

    @patch('time.sleep')
    def test_wait_for_knowledge_section_loaded(self, mock_sleep):
        """Test waiting for knowledge section to load."""
        mock_client = Mock(spec=ChromeClient)
        mock_client.send_command.return_value = {"result": {"value": True}}
        
        extractor = ProjectKnowledgeExtractor(mock_client)
        extractor._wait_for_knowledge_section_loaded()
        
        # Should check for knowledge section
        mock_client.send_command.assert_called()

    @patch('time.sleep')
    @patch('time.time')
    def test_wait_for_knowledge_section_timeout(self, mock_time, mock_sleep):
        """Test timeout when knowledge section doesn't load."""
        mock_client = Mock(spec=ChromeClient)
        mock_client.send_command.return_value = {"result": {"value": False}}
        
        # Simulate timeout
        mock_time.side_effect = [0, 1, 2, 3, 4, 5, 6]
        
        extractor = ProjectKnowledgeExtractor(mock_client)
        with pytest.raises(ExtractionError) as exc_info:
            extractor._wait_for_knowledge_section_loaded(timeout=5)
        
        assert "Timeout waiting for knowledge section" in str(exc_info.value)

    def test_extract_knowledge_files_empty(self):
        """Test extracting when no knowledge files present."""
        mock_client = Mock(spec=ChromeClient)
        mock_client.send_command.return_value = {
            "result": {"value": []}
        }
        
        extractor = ProjectKnowledgeExtractor(mock_client)
        files = extractor._extract_knowledge_files()
        
        assert files == []

    def test_extract_knowledge_files_success(self):
        """Test successful knowledge file extraction."""
        mock_client = Mock(spec=ChromeClient)
        mock_client.send_command.return_value = {
            "result": {
                "value": [
                    {
                        "name": "README.md",
                        "type": "markdown",
                        "size": 1024,
                        "element_id": "file-1"
                    },
                    {
                        "name": "code.py",
                        "type": "python",
                        "size": 2048,
                        "element_id": "file-2"
                    }
                ]
            }
        }
        
        extractor = ProjectKnowledgeExtractor(mock_client)
        files = extractor._extract_knowledge_files()
        
        assert len(files) == 2
        assert files[0]["name"] == "README.md"
        assert files[1]["name"] == "code.py"

    def test_download_file_content(self):
        """Test downloading individual file content."""
        mock_client = Mock(spec=ChromeClient)
        
        # Mock clicking on file and extracting content
        mock_client.send_command.side_effect = [
            {},  # Click response
            {"result": {"value": True}},  # Wait for content
            {"result": {"value": "# Hello World\nThis is content"}}  # Get content
        ]
        
        extractor = ProjectKnowledgeExtractor(mock_client)
        content = extractor._download_file_content("file-1", "README.md")
        
        assert content == "# Hello World\nThis is content"

    @patch('time.sleep')
    def test_extract_project_knowledge_full_flow(self, mock_sleep):
        """Test full flow of extracting knowledge from a project."""
        mock_client = Mock(spec=ChromeClient)
        
        def mock_send_command(method, params):
            if method == "Page.navigate":
                return {"frameId": "123"}
            elif method == "Runtime.evaluate":
                expr = params.get("expression", "")
                
                # Check if knowledge section loaded
                if "knowledge" in expr.lower() and "loaded" in expr.lower():
                    return {"result": {"value": True}}
                
                # Get list of files
                elif "knowledge" in expr.lower() and "files" in expr.lower():
                    return {
                        "result": {
                            "value": [
                                {
                                    "name": "README.md",
                                    "type": "markdown",
                                    "size": 100,
                                    "element_id": "file-1"
                                }
                            ]
                        }
                    }
                
                # Click on file
                elif "click" in expr.lower():
                    return {}
                
                # Wait for content
                elif "content" in expr.lower() and "loaded" in expr.lower():
                    return {"result": {"value": True}}
                
                # Get file content
                elif "content" in expr.lower():
                    return {"result": {"value": "# Project README"}}
            
            return {}
        
        mock_client.send_command.side_effect = mock_send_command
        
        project = Project(
            id="test-id",
            name="Test Project",
            url="https://claude.ai/project/test-id"
        )
        
        extractor = ProjectKnowledgeExtractor(mock_client)
        knowledge_files = extractor.extract_project_knowledge(project)
        
        assert len(knowledge_files) == 1
        assert isinstance(knowledge_files[0], KnowledgeFile)
        assert knowledge_files[0].name == "README.md"
        assert knowledge_files[0].content == "# Project README"
        assert knowledge_files[0].file_type == "markdown"

    def test_extract_project_knowledge_no_files(self):
        """Test extracting from project with no knowledge files."""
        mock_client = Mock(spec=ChromeClient)
        
        mock_client.send_command.side_effect = [
            {"frameId": "123"},  # Navigate
            {"result": {"value": True}},  # Knowledge section loaded
            {"result": {"value": []}}  # No files
        ]
        
        project = Project(
            id="empty-id",
            name="Empty Project",
            url="https://claude.ai/project/empty-id"
        )
        
        extractor = ProjectKnowledgeExtractor(mock_client)
        with patch('time.sleep'):
            knowledge_files = extractor.extract_project_knowledge(project)
        
        assert knowledge_files == []

    @patch('time.sleep')
    def test_extract_project_knowledge_with_retry(self, mock_sleep):
        """Test retry mechanism when extraction fails."""
        mock_client = Mock(spec=ChromeClient)
        
        # First attempt fails, second succeeds
        call_count = 0
        
        def mock_send_command(method, params):
            nonlocal call_count
            call_count += 1
            
            if method == "Page.navigate":
                return {"frameId": "123"}
            elif method == "Runtime.evaluate":
                expr = params.get("expression", "")
                
                # Handle the knowledge section loaded check
                if "knowledgeSection" in expr or "knowledge-section" in expr:
                    return {"result": {"value": True}}
                # Handle file extraction
                elif "fileElements" in expr or "knowledge-file" in expr:
                    if call_count < 5:
                        raise ChromeWebSocketError("Network error")
                    return {"result": {"value": []}}
            
            return {}
        
        mock_client.send_command.side_effect = mock_send_command
        
        project = Project(
            id="retry-id",
            name="Retry Project",
            url="https://claude.ai/project/retry-id"
        )
        
        extractor = ProjectKnowledgeExtractor(mock_client)
        knowledge_files = extractor.extract_project_knowledge(project, retry_count=2)
        
        assert knowledge_files == []

    def test_handle_large_file_content(self):
        """Test handling large file content."""
        mock_client = Mock(spec=ChromeClient)
        
        large_content = "x" * 10000  # 10KB of content
        
        mock_client.send_command.side_effect = [
            {},  # Click
            {"result": {"value": True}},  # Content loaded
            {"result": {"value": large_content}}  # Large content
        ]
        
        extractor = ProjectKnowledgeExtractor(mock_client)
        content = extractor._download_file_content("file-1", "large.txt")
        
        assert content == large_content
        assert len(content) == 10000

    def test_extract_different_file_types(self):
        """Test extracting different types of knowledge files."""
        mock_client = Mock(spec=ChromeClient)
        
        mock_client.send_command.return_value = {
            "result": {
                "value": [
                    {"name": "README.md", "type": "markdown", "element_id": "1"},
                    {"name": "main.py", "type": "python", "element_id": "2"},
                    {"name": "data.json", "type": "json", "element_id": "3"},
                    {"name": "styles.css", "type": "css", "element_id": "4"},
                    {"name": "index.html", "type": "html", "element_id": "5"},
                    {"name": "notes.txt", "type": "text", "element_id": "6"}
                ]
            }
        }
        
        extractor = ProjectKnowledgeExtractor(mock_client)
        files = extractor._extract_knowledge_files()
        
        assert len(files) == 6
        file_types = {f["type"] for f in files}
        assert file_types == {"markdown", "python", "json", "css", "html", "text"}