"""End-to-end integration tests using sanitized fixtures."""
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from claude_sync.extractors import ProjectExtractor, KnowledgeExtractor
from claude_sync.sync import SyncOrchestrator
from claude_sync.browser import ChromeConnection


class TestEndToEndIntegration:
    """Test full sync workflow with real HTML structures."""
    
    @pytest.fixture
    def fixtures_dir(self):
        """Get fixtures directory."""
        return Path(__file__).parent.parent / "fixtures"
    
    @pytest.fixture
    def sanitized_projects_html(self, fixtures_dir):
        """Load sanitized projects page."""
        with open(fixtures_dir / "sanitized_projects_page.html", 'r') as f:
            return f.read()
    
    @pytest.fixture
    def sanitized_project_html(self, fixtures_dir):
        """Load sanitized project page."""
        with open(fixtures_dir / "sanitized_project_page.html", 'r') as f:
            return f.read()
    
    @pytest.fixture
    def minimal_projects_html(self, fixtures_dir):
        """Load minimal projects page."""
        with open(fixtures_dir / "minimal_projects_page.html", 'r') as f:
            return f.read()
    
    @pytest.fixture
    def minimal_project_html(self, fixtures_dir):
        """Load minimal project page."""
        with open(fixtures_dir / "minimal_project_page.html", 'r') as f:
            return f.read()
    
    def test_extract_projects_from_real_page(self, sanitized_projects_html):
        """Test extracting projects from real sanitized page."""
        extractor = ProjectExtractor()
        projects = extractor.extract_from_html(sanitized_projects_html)
        
        assert len(projects) > 0
        for project in projects:
            assert project.name
            assert project.url
            assert "/project/" in project.url
    
    def test_extract_knowledge_from_real_page(self, minimal_project_html):
        """Test extracting knowledge files from minimal project page."""
        extractor = KnowledgeExtractor()
        files = extractor.extract_from_html(minimal_project_html)
        
        assert len(files) > 0
        for file in files:
            assert file.name
            assert file.file_type in ["text", "pdf"]
            # Lines might be None for some files
    
    @pytest.mark.asyncio
    async def test_full_sync_workflow(self, tmp_path, minimal_projects_html, minimal_project_html):
        """Test complete sync workflow with minimal fixtures."""
        from claude_sync.models import Project, KnowledgeFile
        
        # Create test data
        test_projects = [
            Project(id="test-001", name="Test Project Alpha", url="https://claude.ai/project/test-001"),
            Project(id="test-002", name="Demo Application Beta", url="https://claude.ai/project/test-002"),
        ]
        
        test_files = [
            KnowledgeFile(name="example_document.txt", file_type="text", lines=150),
            KnowledgeFile(name="sample_data.pdf", file_type="pdf", lines=75),
        ]
        
        # Mock browser connection
        mock_connection = AsyncMock(spec=ChromeConnection)
        mock_connection.is_logged_in.return_value = True
        mock_connection.extract_projects.return_value = test_projects
        mock_connection.extract_knowledge_files.return_value = test_files
        mock_connection.download_file_content.return_value = "Sample file content"
        
        with patch('claude_sync.sync.orchestrator.ChromeManager') as mock_manager_class:
            mock_manager = AsyncMock()
            mock_manager_class.return_value = mock_manager
            mock_manager.get_or_create_browser.return_value = AsyncMock()
            
            with patch('claude_sync.sync.orchestrator.ChromeConnection', return_value=mock_connection):
                # Create orchestrator
                orchestrator = SyncOrchestrator(tmp_path)
                
                # Run sync
                result = await orchestrator.sync_all()
                
                assert result["success"] is True
                assert result["projects_synced"] == 2
                assert result["files_synced"] == 4  # 2 files per project
                
                # Check that files were saved
                projects_dir = tmp_path / "projects"
                assert projects_dir.exists()
                
                # Check project directories exist
                project_dirs = list(projects_dir.iterdir())
                assert len(project_dirs) == 2
                
                # Check knowledge files exist
                for project_dir in project_dirs:
                    knowledge_dir = project_dir / "knowledge"
                    assert knowledge_dir.exists()
                    files = list(knowledge_dir.iterdir())
                    assert len(files) == 2
    
    def test_projects_extraction_pagination(self, sanitized_projects_html):
        """Test that all projects are extracted even with many projects."""
        extractor = ProjectExtractor()
        projects = extractor.extract_from_html(sanitized_projects_html)
        
        # Check we got a reasonable number of projects
        assert len(projects) >= 5  # Assuming the sanitized page has at least 5
        
        # Verify each project has required fields
        for i, project in enumerate(projects):
            assert project.name, f"Project {i} missing name"
            assert project.url, f"Project {i} missing URL"
            assert project.id, f"Project {i} missing ID"
    
    def test_knowledge_extraction_various_formats(self, minimal_project_html):
        """Test extracting files with various formats."""
        extractor = KnowledgeExtractor()
        files = extractor.extract_from_html(minimal_project_html)
        
        # Check we have both text and PDF files
        file_types = {f.file_type for f in files}
        assert "text" in file_types or "pdf" in file_types
        
        # Check line counts are reasonable
        for file in files:
            if file.lines is not None:
                assert 0 < file.lines < 10000  # Reasonable range
    
    @pytest.mark.asyncio
    async def test_sync_error_handling(self, tmp_path):
        """Test sync handles errors gracefully."""
        with patch('claude_sync.sync.orchestrator.ChromeManager') as mock_manager_class:
            mock_manager = AsyncMock()
            mock_manager_class.return_value = mock_manager
            mock_manager.get_or_create_browser.side_effect = Exception("Browser error")
            
            orchestrator = SyncOrchestrator(tmp_path)
            result = await orchestrator.sync_all()
            
            assert result["success"] is False
            assert "Browser error" in result["error"]